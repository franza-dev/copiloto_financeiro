"""
Guido — WhatsApp Handler
Recebe mensagens via webhook do Evolution API, identifica o usuário pelo
telefone, e processa lançamentos/consultas usando a mesma IA e API.
"""
import os
import base64
import tempfile
import requests as http_requests
from datetime import date
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
import database
import ia_engine

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

# URL do Evolution API (container na mesma rede Docker)
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://evolution-api:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "guido")


# ==========================================
# HELPERS
# ==========================================

def _normalizar_telefone(telefone: str) -> str:
    """Remove tudo que não é dígito e garante prefixo 55."""
    apenas_digitos = ''.join(c for c in str(telefone) if c.isdigit())
    # Remove @s.whatsapp.net se vier do Evolution API
    apenas_digitos = apenas_digitos.split('@')[0]
    if not apenas_digitos.startswith("55"):
        apenas_digitos = "55" + apenas_digitos
    return apenas_digitos


def _reconectar_evolution() -> bool:
    """Reinicia a instância da Evolution API. Retorna True se OK."""
    try:
        url = f"{EVOLUTION_API_URL}/instance/restart/{EVOLUTION_INSTANCE}"
        headers = {"apikey": EVOLUTION_API_KEY}
        resp = http_requests.post(url, headers=headers, timeout=15)
        print(f"[WhatsApp] Restart da instância: {resp.status_code}")
        import time
        time.sleep(8)  # aguarda reconexão
        return resp.status_code < 400
    except Exception as e:
        print(f"[WhatsApp] Erro ao reconectar: {e}")
        return False


def _enviar_whatsapp(telefone: str, texto: str, _retry: bool = False):
    """Envia mensagem via Evolution API. Se detectar 'Connection Closed',
    reinicia a instância automaticamente e tenta de novo (1 retry)."""
    try:
        url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
        payload = {"number": telefone, "text": texto}
        headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
        resp = http_requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"[WhatsApp] Enviado pra {telefone}: {resp.status_code}")

        if resp.status_code >= 400:
            corpo_erro = resp.text[:500]
            print(f"[WhatsApp] ERRO resposta: {corpo_erro}")

            # Self-healing: se a conexão caiu silenciosamente, reinicia a
            # instância e tenta uma vez. Só tenta uma vez pra não entrar em loop.
            if not _retry and "Connection Closed" in corpo_erro:
                print(f"[WhatsApp] Detectada conexão caída — tentando auto-reconexão...")
                if _reconectar_evolution():
                    _enviar_whatsapp(telefone, texto, _retry=True)
    except Exception as e:
        print(f"[WhatsApp] Erro ao enviar mensagem: {e}")


def _buscar_usuario_por_telefone(db: Session, telefone: str):
    """Busca usuário pelo telefone normalizado."""
    return db.query(models.Usuario).filter(models.Usuario.telefone == telefone).first()


def _baixar_audio_whatsapp(message_data: dict) -> str | None:
    """Baixa áudio de uma mensagem WhatsApp via Evolution API.

    Usa o endpoint getBase64FromMediaMessage pra pegar o áudio em base64,
    decodifica e salva como arquivo temporário. Retorna o path do arquivo
    ou None se falhar.
    """
    try:
        key = message_data.get("key", {})
        message_id = key.get("id")
        remote_jid = key.get("remoteJid")

        if not message_id or not remote_jid:
            print("[WhatsApp] Áudio sem key/id/remoteJid")
            return None

        # Pega o áudio como base64 via Evolution API
        url = f"{EVOLUTION_API_URL}/chat/getBase64FromMediaMessage/{EVOLUTION_INSTANCE}"
        payload = {
            "message": {
                "key": {
                    "remoteJid": remote_jid,
                    "id": message_id,
                }
            }
        }
        headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
        resp = http_requests.post(url, json=payload, headers=headers, timeout=30)

        if resp.status_code not in (200, 201):
            print(f"[WhatsApp] Erro ao baixar áudio: {resp.status_code} {resp.text[:200]}")
            return None

        data = resp.json()
        b64_data = data.get("base64", "")
        mimetype = data.get("mimetype", "audio/ogg")

        if not b64_data:
            print("[WhatsApp] Áudio base64 vazio")
            return None

        # Remove prefixo data:audio/... se existir
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]

        # Decodifica e salva como arquivo temporário
        audio_bytes = base64.b64decode(b64_data)
        ext = ".ogg" if "ogg" in mimetype else ".mp4" if "mp4" in mimetype else ".wav"
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False, prefix="guido_audio_")
        tmp.write(audio_bytes)
        tmp.close()
        print(f"[WhatsApp] Áudio salvo: {tmp.name} ({len(audio_bytes)} bytes)")
        return tmp.name

    except Exception as e:
        print(f"[WhatsApp] Erro ao processar áudio: {e}")
        return None


def _contas_do_usuario(db: Session, usuario_id: int) -> list:
    """Lista de contas formatada pra injetar no prompt da IA."""
    contas = db.query(models.ContaBancaria).filter(
        models.ContaBancaria.usuario_id == usuario_id
    ).all()
    return [
        {
            "id": c.id,
            "nome": c.nome,
            "banco": c.banco,
            "tipo": c.tipo,
            "modalidade": c.modalidade or "corrente",
        }
        for c in contas
    ]


# ==========================================
# FLUXO DE VINCULAÇÃO (primeira mensagem)
# ==========================================

# Sessões temporárias de vinculação: telefone → "aguardando_email"
_sessoes_vinculacao = {}


def _processar_vinculacao(telefone: str, texto: str, db: Session) -> str:
    """Gerencia o fluxo de vincular um número de WhatsApp a um usuário.

    Segurança: o usuário precisa ter cadastrado o MESMO telefone no app web.
    Se o telefone do WhatsApp não bate com o cadastrado → rejeita.

    Retorna a mensagem pra enviar pro usuário."""

    # Passo 1: se estamos esperando o email desse telefone
    if telefone in _sessoes_vinculacao:
        email = texto.strip().lower()

        # Busca o usuário pelo email
        usuario = db.query(models.Usuario).filter(
            models.Usuario.email == email
        ).first()

        if not usuario:
            del _sessoes_vinculacao[telefone]
            return (
                "Não encontrei esse email. 🤔\n\n"
                "Se ainda não tem conta, cria em:\n"
                "👉 app.chamaoguido.com\n\n"
                "Quando criar, coloca seu número de WhatsApp no cadastro."
            )

        # Double check: telefone cadastrado no app precisa bater
        if usuario.telefone and usuario.telefone != telefone:
            del _sessoes_vinculacao[telefone]
            return (
                "Esse email tá cadastrado com outro número de WhatsApp. 🔒\n\n"
                "Se trocou de número, entra no app pra atualizar:\n"
                "👉 app.chamaoguido.com"
            )

        # Se o usuário não tinha telefone cadastrado, salva agora
        if not usuario.telefone:
            usuario.telefone = telefone
            db.commit()

        del _sessoes_vinculacao[telefone]
        return (
            f"Pronto, {usuario.nome.split()[0]}! Te reconheci. ✅\n\n"
            "A partir de agora, é só me mandar o que você gastou.\n\n"
            "Exemplos:\n"
            '• "gastei 80 em esmalte"\n'
            '• "recebi 500 do cliente"\n'
            '• "quanto gastei esse mês?"\n'
            '• "como tá meu saldo?"'
        )

    # Passo 0: primeira mensagem de um número desconhecido
    _sessoes_vinculacao[telefone] = True
    return (
        "Oi! Eu sou o Guido, seu braço direito financeiro. 🤓\n\n"
        "Pra te reconhecer com segurança, me manda o *email* que você "
        "usou pra criar sua conta no app.\n\n"
        "Se ainda não tem conta, cria em:\n"
        "👉 app.chamaoguido.com"
    )


# ==========================================
# PROCESSAMENTO DE MENSAGENS (usuário já vinculado)
# ==========================================

def _eh_consulta(texto: str) -> bool:
    """Detecta se a mensagem é uma consulta de saldo/metas (não um lançamento)."""
    termos = [
        "quanto gastei", "quanto eu gastei", "meu saldo", "como tá",
        "como está", "resumo", "meta", "teto", "limite", "saldo",
        "sobrou", "quanto falta", "quanto tenho", "balanço",
        "quanto posso", "quanto ainda", "quanto resta", "categoria",
    ]
    texto_lower = texto.lower()
    return any(t in texto_lower for t in termos)


def _consulta_categoria_especifica(texto: str, db: Session, usuario_id: int) -> str | None:
    """Se o usuário pergunta sobre uma categoria específica, retorna o saldo detalhado.
    Retorna None se não detectar categoria na pergunta."""
    from datetime import date as _date
    texto_lower = texto.lower()

    # Busca todos os limites do usuário
    limites = db.query(models.LimiteCategoria).filter(
        models.LimiteCategoria.usuario_id == usuario_id
    ).all()
    if not limites:
        return None

    # Tenta encontrar qual categoria o usuário está perguntando
    categoria_encontrada = None
    for lim in limites:
        cat_lower = lim.categoria.lower()
        # Checa se o nome da categoria (ou parte significativa) aparece na pergunta
        # Ex: "alimentação" em "quanto tenho de alimentação?"
        # Ex: "transporte" em "como tá meu teto de transporte?"
        palavras_cat = cat_lower.split()
        for palavra in palavras_cat:
            if len(palavra) >= 4 and palavra in texto_lower:
                categoria_encontrada = lim
                break
        if categoria_encontrada:
            break

    if not categoria_encontrada:
        return None

    # Calcula gasto do mês atual nessa categoria
    hoje = _date.today()
    prefixo = f"{hoje.year:04d}-{hoje.month:02d}"
    gasto = db.query(func.sum(models.Transacao.valor)).filter(
        models.Transacao.usuario_id == usuario_id,
        models.Transacao.confirmado == True,
        models.Transacao.categoria == categoria_encontrada.categoria,
        models.Transacao.data.like(f"{prefixo}%"),
        models.Transacao.valor < 0,
        models.Transacao.categoria != "Transferência Interna",
    ).scalar() or 0

    gasto_abs = abs(gasto)
    teto = categoria_encontrada.valor_teto
    disponivel = max(teto - gasto_abs, 0)
    pct_usado = (gasto_abs / teto * 100) if teto > 0 else 0
    pct_disponivel = max(100 - pct_usado, 0)

    if pct_usado > 100:
        emoji = "🔴"
        status = f"Você já *estourou* o teto em R$ {gasto_abs - teto:,.2f}!"
    elif pct_usado >= 70:
        emoji = "🟡"
        status = "Atenção, tá chegando perto do limite."
    else:
        emoji = "🟢"
        status = "Tá tranquilo por enquanto."

    return (
        f"{emoji} *{categoria_encontrada.categoria}*\n\n"
        f"🎯 Teto mensal: R$ {teto:,.2f}\n"
        f"💸 Gasto esse mês: R$ {gasto_abs:,.2f}\n"
        f"💰 Disponível: R$ {disponivel:,.2f}\n"
        f"📊 Usado: {pct_usado:.0f}% · Disponível: {pct_disponivel:.0f}%\n\n"
        f"{status}"
    )


def _eh_saudacao_ou_conversa(texto: str) -> bool:
    """Detecta se a mensagem é uma saudação ou conversa casual (não financeira)."""
    texto_lower = texto.lower().strip().rstrip("!?.,:;")
    # Saudações diretas
    saudacoes = [
        "oi", "olá", "ola", "hey", "eai", "e aí", "fala", "bom dia",
        "boa tarde", "boa noite", "tudo bem", "tudo bom", "como vai",
        "opa", "salve", "hello", "hi", "obrigado", "obrigada", "valeu",
        "vlw", "brigado", "brigada", "tchau", "até mais", "ate mais",
        "flw", "falou",
    ]
    if any(texto_lower == s or texto_lower.startswith(s + " ") for s in saudacoes):
        return True
    # Mensagens muito curtas sem números provavelmente não são lançamentos
    if len(texto_lower) < 8 and not any(c.isdigit() for c in texto_lower):
        return True
    return False


def _responder_conversa(texto: str, nome: str) -> str:
    """Gera uma resposta conversacional amigável com viés financeiro."""
    texto_lower = texto.lower().strip()

    if any(s in texto_lower for s in ["bom dia", "boa tarde", "boa noite"]):
        periodo = "dia"
        if "tarde" in texto_lower:
            periodo = "tarde"
        elif "noite" in texto_lower:
            periodo = "noite"
        return (
            f"Boa {periodo}, {nome}! 😊\n\n"
            "Tô aqui pra te ajudar com o dinheiro.\n\n"
            "Me manda o que gastou ou pergunte como tá o mês. Alguns exemplos:\n"
            '• *"gastei 80 em esmalte"*\n'
            '• *"recebi 500 do cliente"*\n'
            '• *"quanto gastei esse mês?"*\n'
            '• *"como tá meu saldo?"*'
        )

    if any(s in texto_lower for s in ["obrigad", "valeu", "vlw", "brigad"]):
        return f"Sempre às ordens, {nome}! 💪\nQuando precisar, é só chamar."

    if any(s in texto_lower for s in ["tchau", "até", "ate", "flw", "falou"]):
        return f"Até mais, {nome}! 👋\nTô aqui 24h se precisar."

    # Saudação genérica
    return (
        f"E aí, {nome}! 👋 Sou o Guido, seu braço direito financeiro.\n\n"
        "Me conta o que rolou:\n"
        '• *"gastei 45 no uber pra reunião"*\n'
        '• *"comprei 150 no crédito do Nubank"*\n'
        '• *"quanto gastei esse mês?"*\n'
        '• *"como tá o teto de alimentação?"*\n\n'
        "Pode mandar por texto que eu organizo tudo pra você. 🤓"
    )


def _gerar_resumo(db: Session, usuario_id: int) -> str:
    """Gera resumo financeiro do mês atual formatado pra WhatsApp."""
    hoje = date.today()
    prefixo = f"{hoje.year:04d}-{hoje.month:02d}"

    def calc(tipo, sinal):
        q = db.query(func.sum(models.Transacao.valor)).filter(
            models.Transacao.tipo == tipo,
            models.Transacao.confirmado == True,
            models.Transacao.usuario_id == usuario_id,
            models.Transacao.categoria != "Transferência Interna",
            (models.Transacao.valor > 0 if sinal == "+" else models.Transacao.valor < 0),
            models.Transacao.data.like(f"{prefixo}%"),
        )
        return q.scalar() or 0

    rpj, dpj = calc("PJ", "+"), calc("PJ", "-")
    rpf, dpf = calc("PF", "+"), calc("PF", "-")

    linhas = [f"📊 *Seu resumo de {hoje.strftime('%B/%Y')}*\n"]

    if rpj > 0 or dpj < 0:
        linhas.append(f"🏢 *Negócio*")
        linhas.append(f"   ↗ Entrou: R$ {rpj:,.2f}")
        linhas.append(f"   ↙ Saiu: R$ {abs(dpj):,.2f}")
        linhas.append(f"   💰 Sobrou: R$ {rpj + dpj:,.2f}\n")

    if rpf > 0 or dpf < 0:
        linhas.append(f"🏠 *Casa*")
        linhas.append(f"   ↗ Entrou: R$ {rpf:,.2f}")
        linhas.append(f"   ↙ Saiu: R$ {abs(dpf):,.2f}")
        linhas.append(f"   💰 Sobrou: R$ {rpf + dpf:,.2f}\n")

    if rpj == 0 and dpj == 0 and rpf == 0 and dpf == 0:
        linhas.append("Nada registrado esse mês ainda. Me manda um gasto!")

    # Metas próximas do limite
    limites = db.query(models.LimiteCategoria).filter(
        models.LimiteCategoria.usuario_id == usuario_id
    ).all()

    if limites:
        # Calcula gastos por categoria no mês
        gastos_cat = {}
        txs = db.query(models.Transacao).filter(
            models.Transacao.usuario_id == usuario_id,
            models.Transacao.confirmado == True,
            models.Transacao.valor < 0,
            models.Transacao.data.like(f"{prefixo}%"),
            models.Transacao.categoria != "Transferência Interna",
        ).all()
        for tx in txs:
            gastos_cat[tx.categoria] = gastos_cat.get(tx.categoria, 0) + abs(tx.valor)

        alertas = []
        for lim in limites:
            gasto = gastos_cat.get(lim.categoria, 0)
            pct = gasto / lim.valor_teto if lim.valor_teto > 0 else 0
            if pct >= 0.7:
                emoji = "🔴" if pct > 1 else "🟡"
                alertas.append(f"   {emoji} {lim.categoria}: R$ {gasto:,.2f} de R$ {lim.valor_teto:,.2f} ({pct:.0%})")

        if alertas:
            linhas.append("🎯 *Metas que merecem atenção:*")
            linhas.extend(alertas)

    return "\n".join(linhas)


def _categorias_para_ia(db: Session) -> list:
    """Monta lista de categorias (base + personalizadas) pra injetar no prompt."""
    from main import LISTA_CATEGORIAS_BASE
    cats = list(LISTA_CATEGORIAS_BASE)
    try:
        personalizadas = db.query(models.Categoria).all()
        for c in personalizadas:
            if c.nome not in cats:
                cats.append(c.nome)
    except Exception:
        pass
    return sorted(cats)


def _processar_lancamento(texto: str, db: Session, usuario_id: int) -> str:
    """Processa um lançamento por TEXTO via IA."""
    contas = _contas_do_usuario(db, usuario_id)
    cats = _categorias_para_ia(db)
    dados_ia = ia_engine.processar_texto_ia(texto, contas=contas, categorias=cats)
    return _processar_lancamento_from_ia(dados_ia, db, usuario_id)


def _processar_lancamento_from_ia(dados_ia: dict, db: Session, usuario_id: int) -> str:
    """Processa o resultado da IA (comum pra texto e áudio)."""

    # Config de limite
    if dados_ia.get("natureza") == "config_limite":
        limite = db.query(models.LimiteCategoria).filter(
            models.LimiteCategoria.categoria == dados_ia["categoria"]
        ).first()
        if limite:
            limite.valor_teto = dados_ia["valor"]
        else:
            db.add(models.LimiteCategoria(
                categoria=dados_ia["categoria"],
                valor_teto=dados_ia["valor"],
                usuario_id=usuario_id,
            ))
        db.commit()
        return f"🎯 Teto de R$ {dados_ia['valor']:.2f} pra {dados_ia['categoria']} salvo!"

    # Lançamento de transação
    hoje = date.today().isoformat()

    # Valida conta_id
    conta_id = None
    if dados_ia.get("conta_id"):
        try:
            cid = int(dados_ia["conta_id"])
            conta = db.query(models.ContaBancaria).filter(
                models.ContaBancaria.id == cid,
                models.ContaBancaria.usuario_id == usuario_id,
            ).first()
            if conta:
                conta_id = conta.id
        except (TypeError, ValueError):
            pass

    # Fallback fuzzy
    if conta_id is None and dados_ia.get("banco"):
        termo = dados_ia["banco"].lower()
        conta = db.query(models.ContaBancaria).filter(
            (models.ContaBancaria.nome.ilike(f"%{termo}%")) | (models.ContaBancaria.banco.ilike(f"%{termo}%")),
            models.ContaBancaria.tipo == dados_ia.get("tipo", "PF"),
            models.ContaBancaria.usuario_id == usuario_id,
        ).first()
        if conta:
            conta_id = conta.id

    # Calcula data de caixa
    from main import resolver_data_caixa
    data_caixa = resolver_data_caixa(db, conta_id, hoje)

    valor = float(dados_ia.get("valor", 0))
    if dados_ia.get("natureza") == "saida":
        valor = -abs(valor)
    else:
        valor = abs(valor)

    categoria = dados_ia.get("categoria", "A Classificar")
    tipo = dados_ia.get("tipo", "PF")
    descricao = dados_ia.get("descricao", "Lançamento por áudio")

    # Decide: vai direto ou quarentena
    vai_direto = bool(categoria and categoria != "A Classificar" and conta_id)

    nova_tx = models.Transacao(
        data=hoje,
        data_caixa=data_caixa,
        descricao=descricao,
        valor=valor,
        categoria=categoria,
        tipo=tipo,
        conta_id=conta_id,
        usuario_id=usuario_id,
        confirmado=vai_direto,
    )
    db.add(nova_tx)
    db.commit()

    # Monta resposta
    tipo_label = "🏢 Negócio" if tipo == "PJ" else "🏠 Casa"
    sinal = "saiu" if valor < 0 else "entrou"
    valor_abs = abs(valor)

    resposta = f"Anotado. ✅\n\n"
    resposta += f"💰 R$ {valor_abs:,.2f} {sinal}\n"
    resposta += f"📂 {categoria} · {tipo_label}\n"
    resposta += f"📝 {descricao}\n"

    if conta_id:
        conta_obj = db.query(models.ContaBancaria).filter(models.ContaBancaria.id == conta_id).first()
        if conta_obj:
            icone = "💳" if conta_obj.modalidade == "cartao_credito" else "🏦"
            resposta += f"{icone} {conta_obj.nome}\n"

    if not vai_direto:
        resposta += "\n⏳ Mandei pra revisão no app. Confirma lá quando puder."
    else:
        # Mostra gasto total do mês nessa categoria
        prefixo = f"{date.today().year:04d}-{date.today().month:02d}"
        total_cat = db.query(func.sum(models.Transacao.valor)).filter(
            models.Transacao.usuario_id == usuario_id,
            models.Transacao.confirmado == True,
            models.Transacao.categoria == categoria,
            models.Transacao.data.like(f"{prefixo}%"),
            models.Transacao.valor < 0,
        ).scalar() or 0
        resposta += f"\n📊 Esse mês em {categoria}: R$ {abs(total_cat):,.2f}"

        # Checa teto
        limite = db.query(models.LimiteCategoria).filter(
            models.LimiteCategoria.categoria == categoria,
            models.LimiteCategoria.usuario_id == usuario_id,
        ).first()
        if limite and limite.valor_teto > 0:
            pct = abs(total_cat) / limite.valor_teto
            if pct > 1:
                resposta += f"\n⚠️ Cuidado, você já atingiu {pct:.0%} do teto de R$ {limite.valor_teto:,.2f}!"
            elif pct >= 0.7:
                resposta += f"\n🟡 Atenção: {pct:.0%} do teto de R$ {limite.valor_teto:,.2f}"

    return resposta


# ==========================================
# WEBHOOK ENDPOINT
# ==========================================

@router.post("/webhook")
async def webhook_evolution(request: Request, db: Session = Depends(database.get_db)):
    """Recebe webhooks do Evolution API quando chega mensagem no WhatsApp."""
    try:
        body = await request.json()
    except Exception:
        return {"status": "ok"}

    # Evolution API envia vários tipos de evento — só processamos mensagens novas
    event = body.get("event", "")
    if event not in ("messages.upsert",):
        return {"status": "ignored", "event": event}

    data = body.get("data", {})
    key = data.get("key", {})

    # Ignora mensagens enviadas por nós mesmos
    if key.get("fromMe", False):
        return {"status": "ignored", "reason": "fromMe"}

    # Extrai telefone e texto
    remote_jid = key.get("remoteJid", "")
    if not remote_jid or "@g.us" in remote_jid:
        # Ignora mensagens de grupos
        return {"status": "ignored", "reason": "group"}

    telefone = _normalizar_telefone(remote_jid)

    # Extrai texto da mensagem (suporta diferentes formatos do Evolution API)
    message = data.get("message", {})
    texto = (
        message.get("conversation")
        or message.get("extendedTextMessage", {}).get("text")
        or ""
    ).strip()

    # Detecta se é mensagem de áudio
    eh_audio = bool(message.get("audioMessage"))

    if not texto and not eh_audio:
        # Imagem, vídeo, sticker, etc — não processamos
        _enviar_whatsapp(telefone, "Por enquanto entendo texto e áudio. 😅 Me escreve ou grava o que gastou!")
        return {"status": "ok", "reason": "unsupported-type"}

    # Fluxo principal
    usuario = _buscar_usuario_por_telefone(db, telefone)

    if not usuario:
        if eh_audio:
            _enviar_whatsapp(telefone, "Opa, antes de mandar áudio preciso te reconhecer. 😊 Me manda seu email cadastrado.")
            return {"status": "ok", "reason": "audio-sem-vinculo"}
        # Usuário não vinculado — fluxo de vinculação
        resposta = _processar_vinculacao(telefone, texto, db)
    elif eh_audio:
        # Processa áudio via Gemini
        _enviar_whatsapp(telefone, "🎧 Tô ouvindo seu áudio...")
        audio_path = _baixar_audio_whatsapp(data)
        if audio_path:
            try:
                contas = _contas_do_usuario(db, usuario.id)
                cats = _categorias_para_ia(db)
                dados_ia = ia_engine.processar_audio_ia(audio_path, contas=contas, categorias=cats)
                # Reutiliza a mesma lógica de lançamento
                if dados_ia.get("natureza") == "config_limite":
                    resposta = _processar_lancamento_from_ia(dados_ia, db, usuario.id)
                else:
                    resposta = _processar_lancamento_from_ia(dados_ia, db, usuario.id)
            except Exception as e:
                print(f"[WhatsApp] Erro ao processar áudio: {e}")
                resposta = "Não consegui entender o áudio. 😕 Tenta mandar de novo ou escreve o que gastou."
            finally:
                # Limpa arquivo temporário
                try:
                    os.remove(audio_path)
                except Exception:
                    pass
        else:
            resposta = "Não consegui baixar o áudio. 😕 Tenta mandar de novo?"
    elif _eh_saudacao_ou_conversa(texto):
        # Saudação ou conversa casual — responde amigavelmente
        resposta = _responder_conversa(texto, usuario.nome.split()[0])
    elif _eh_consulta(texto):
        # Primeiro tenta consulta de categoria específica
        resposta_cat = _consulta_categoria_especifica(texto, db, usuario.id)
        if resposta_cat:
            resposta = resposta_cat
        else:
            # Consulta geral de saldo/metas
            resposta = _gerar_resumo(db, usuario.id)
    else:
        # Lançamento de transação por texto
        resposta = _processar_lancamento(texto, db, usuario.id)

    _enviar_whatsapp(telefone, resposta)
    return {"status": "ok"}


@router.get("/status")
def whatsapp_status():
    """Health check do módulo WhatsApp."""
    return {"status": "online", "evolution_url": EVOLUTION_API_URL, "instance": EVOLUTION_INSTANCE}
