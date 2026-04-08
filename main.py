from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from calendar import monthrange
import hashlib
import shutil
import os
import json

# Meus arquivos locais
import models, database, ia_engine

# --- UTILITÁRIOS ---
def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_senha(senha: str, hash_salvo: str) -> bool:
    return hashlib.sha256(senha.encode()).hexdigest() == (hash_salvo or "")

# --- INICIALIZAÇÃO DO BANCO ---
models.Base.metadata.create_all(bind=database.engine)

# Migrações idempotentes — cada ALTER fica envolvido num try/except
# porque PostgreSQL não tem `ADD COLUMN IF NOT EXISTS` em todas as versões.
_MIGRACOES = [
    # Fase 0 (legado)
    "ALTER TABLE usuarios ADD COLUMN senha_hash VARCHAR",
    # Fase 1 — cartão de crédito (contas)
    "ALTER TABLE contas ADD COLUMN modalidade VARCHAR DEFAULT 'corrente'",
    "ALTER TABLE contas ADD COLUMN dia_fechamento INTEGER",
    "ALTER TABLE contas ADD COLUMN dia_vencimento INTEGER",
    "ALTER TABLE contas ADD COLUMN limite FLOAT",
    # Fase 1 — datas competência/caixa + transferências (transações)
    "ALTER TABLE transacoes ADD COLUMN data_caixa VARCHAR",
    "ALTER TABLE transacoes ADD COLUMN tx_transferencia_id INTEGER",
    # WhatsApp — telefone do usuário pra vinculação
    "ALTER TABLE usuarios ADD COLUMN telefone VARCHAR",
    # Assinatura (Asaas)
    "ALTER TABLE usuarios ADD COLUMN assinatura_cliente_asaas VARCHAR",
    "ALTER TABLE usuarios ADD COLUMN assinatura_id_asaas VARCHAR",
    "ALTER TABLE usuarios ADD COLUMN assinatura_ativa_ate VARCHAR",
]
with database.engine.connect() as _conn:
    for _sql in _MIGRACOES:
        try:
            _conn.execute(text(_sql))
            _conn.commit()
        except Exception:
            _conn.rollback()  # coluna já existe, segue a vida

# Backfill único: preenche `data_caixa` nas transações antigas com o valor de `data`
# (conta corrente: competência == caixa). Só roda em linhas onde data_caixa está NULL.
with database.engine.connect() as _conn:
    try:
        _conn.execute(text("UPDATE transacoes SET data_caixa = data WHERE data_caixa IS NULL"))
        _conn.commit()
    except Exception:
        _conn.rollback()

# ==========================================
# CARTÃO DE CRÉDITO — cálculo de data de caixa
# ==========================================
def calcular_data_caixa(data_compra_iso: str, dia_fechamento: int, dia_vencimento: int) -> str:
    """Dada a data de uma compra no cartão e os dias de fechamento/vencimento,
    retorna a data em que o dinheiro vai sair da conta corrente (ISO YYYY-MM-DD).

    Regra:
      1. Encontra o próximo fechamento >= data da compra.
      2. A data de caixa é o próximo dia_vencimento após esse fechamento.
      3. Se o dia de vencimento não existe no mês destino (ex: 31 em fevereiro),
         usa o último dia disponível.
    """
    try:
        d = date.fromisoformat(data_compra_iso[:10])
    except ValueError:
        # Data em formato inesperado — devolve ela mesma pra não quebrar o fluxo
        return data_compra_iso

    # Passo 1: encontrar o mês do próximo fechamento >= d
    if d.day <= dia_fechamento:
        ano_f, mes_f = d.year, d.month
    else:
        if d.month == 12:
            ano_f, mes_f = d.year + 1, 1
        else:
            ano_f, mes_f = d.year, d.month + 1

    # Passo 2: escolher o mês do vencimento
    # Se vencimento > fechamento no mesmo mês, vence no próprio mês do fechamento.
    # Caso contrário (padrão dos cartões brasileiros), vence no mês seguinte.
    if dia_vencimento > dia_fechamento:
        ano_v, mes_v = ano_f, mes_f
    else:
        if mes_f == 12:
            ano_v, mes_v = ano_f + 1, 1
        else:
            ano_v, mes_v = ano_f, mes_f + 1

    # Passo 3: clampear o dia de vencimento se ultrapassar o último dia do mês
    ultimo_dia = monthrange(ano_v, mes_v)[1]
    dia_v = min(dia_vencimento, ultimo_dia)

    return date(ano_v, mes_v, dia_v).isoformat()


def resolver_data_caixa(db: Session, conta_id: Optional[int], data_competencia: str) -> str:
    """Dada uma conta e uma data de competência, retorna a data de caixa correta.
    Conta corrente (ou conta não encontrada) → data_caixa == data_competencia.
    Cartão de crédito → data_caixa calculada pelo fechamento/vencimento."""
    if not conta_id or not data_competencia:
        return data_competencia or ""

    conta = db.query(models.ContaBancaria).filter(models.ContaBancaria.id == conta_id).first()
    if not conta or conta.modalidade != "cartao_credito":
        return data_competencia

    if not conta.dia_fechamento or not conta.dia_vencimento:
        # Cartão mal configurado — degrada pra conta corrente
        return data_competencia

    return calcular_data_caixa(data_competencia, conta.dia_fechamento, conta.dia_vencimento)


app = FastAPI(
    title="Guido API",
    description="Seu braço direito pra separar o dinheiro da casa do dinheiro do negócio. chamaoguido.com.br",
    version="1.0.0",
)

# Registra rotas do WhatsApp
from whatsapp_handler import router as whatsapp_router
app.include_router(whatsapp_router)

# Registra rotas do Asaas (pagamento)
from asaas_handler import router as asaas_router
app.include_router(asaas_router)

# --- SCHEMAS (Envelopes Pydantic) ---
class ConfirmacaoGasto(BaseModel):
    data: str
    descricao: str
    valor: float
    categoria: str
    tipo: str
    conta_id: int

class LimiteCreate(BaseModel):
    categoria: str
    valor_teto: float
    usuario_id: int    

class TransacaoImportada(BaseModel):
    data: str
    descricao: str
    valor: float

class LoteTransacoes(BaseModel):
    conta_id: int
    usuario_id: int
    transacoes: List[TransacaoImportada]

class ContaCreate(BaseModel):
    nome: str
    banco: str
    tipo: str                              # PF | PJ
    usuario_id: int
    modalidade: str = "corrente"           # corrente | cartao_credito
    dia_fechamento: Optional[int] = None   # obrigatório se modalidade=cartao_credito
    dia_vencimento: Optional[int] = None   # idem
    limite: Optional[float] = None         # opcional, só informativo por enquanto

class PagamentoFatura(BaseModel):
    cartao_id: int           # conta de cartão que está sendo paga
    conta_origem_id: int     # conta corrente de onde sai o dinheiro
    valor: float             # valor a pagar (positivo)
    data: str                # data do pagamento ISO YYYY-MM-DD
    usuario_id: int

class RegistroUsuario(BaseModel):
    nome: str
    email: str
    senha: str
    telefone: Optional[str] = None  # +5511999999999 — vincula WhatsApp

class LoginUsuario(BaseModel):
    email: str
    senha: str

class AtualizarPerfil(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    senha_atual: Optional[str] = None
    senha_nova: Optional[str] = None

class CategoriaCreate(BaseModel):
    nome: str
    tipo: str = "Ambos"

# --- 1. ROTAS DE AUTENTICAÇÃO ---

@app.post("/auth/registrar")
def registrar_usuario(dados: RegistroUsuario, db: Session = Depends(database.get_db)):
    if db.query(models.Usuario).filter(models.Usuario.email == dados.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    if dados.telefone:
        tel_existente = db.query(models.Usuario).filter(models.Usuario.telefone == dados.telefone).first()
        if tel_existente:
            raise HTTPException(status_code=400, detail="Esse telefone já está vinculado a outra conta")
    novo = models.Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
        telefone=dados.telefone or None,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

@app.post("/auth/login")
def login_usuario(dados: LoginUsuario, db: Session = Depends(database.get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == dados.email).first()
    if not usuario or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    return usuario

@app.get("/auth/minha-conta")
def minha_conta(usuario_id: int, db: Session = Depends(database.get_db)):
    u = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404)
    return {
        "id": u.id,
        "nome": u.nome,
        "email": u.email,
        "telefone": u.telefone,
        "assinatura_ativa_ate": u.assinatura_ativa_ate,
        "assinatura_status": (
            "ativa" if u.assinatura_ativa_ate and u.assinatura_ativa_ate >= date.today().isoformat()
            else "inativa" if u.assinatura_ativa_ate
            else "sem_assinatura"
        ),
    }

@app.put("/auth/perfil")
def atualizar_perfil(dados: AtualizarPerfil, usuario_id: int, db: Session = Depends(database.get_db)):
    u = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404)

    if dados.nome and dados.nome.strip():
        u.nome = dados.nome.strip()

    if dados.email and dados.email.strip():
        email_novo = dados.email.strip().lower()
        if email_novo != u.email:
            existente = db.query(models.Usuario).filter(models.Usuario.email == email_novo).first()
            if existente:
                raise HTTPException(status_code=400, detail="Esse email já está em uso por outra conta")
            u.email = email_novo

    if dados.telefone is not None:
        tel = ''.join(c for c in dados.telefone if c.isdigit()) if dados.telefone else None
        if tel and not tel.startswith("55"):
            tel = "55" + tel
        if tel and tel != u.telefone:
            existente = db.query(models.Usuario).filter(models.Usuario.telefone == tel).first()
            if existente:
                raise HTTPException(status_code=400, detail="Esse telefone já está vinculado a outra conta")
        u.telefone = tel or u.telefone

    if dados.senha_nova:
        if not dados.senha_atual:
            raise HTTPException(status_code=400, detail="Informe a senha atual pra trocar")
        if not verificar_senha(dados.senha_atual, u.senha_hash):
            raise HTTPException(status_code=400, detail="Senha atual incorreta")
        if len(dados.senha_nova) < 6:
            raise HTTPException(status_code=400, detail="A nova senha precisa ter pelo menos 6 caracteres")
        u.senha_hash = hash_senha(dados.senha_nova)

    db.commit()
    return {"status": "Perfil atualizado"}

@app.post("/auth/cancelar-assinatura")
def cancelar_assinatura(usuario_id: int, db: Session = Depends(database.get_db)):
    """Cancela a assinatura no Asaas mas mantém acesso até o fim do período pago."""
    u = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404)

    if not u.assinatura_id_asaas:
        raise HTTPException(status_code=400, detail="Nenhuma assinatura ativa encontrada")

    # Cancela no Asaas
    import os
    import requests as http_req
    asaas_key = os.getenv("ASAAS_API_KEY", "")
    if asaas_key:
        try:
            resp = http_req.delete(
                f"https://api.asaas.com/v3/subscriptions/{u.assinatura_id_asaas}",
                headers={"access_token": asaas_key},
                timeout=10,
            )
            print(f"[Asaas] Cancelamento subscription {u.assinatura_id_asaas}: {resp.status_code}")
        except Exception as e:
            print(f"[Asaas] Erro ao cancelar: {e}")

    # Limpa o subscription_id mas MANTÉM assinatura_ativa_ate (acesso até vencer)
    u.assinatura_id_asaas = None
    db.commit()

    return {
        "status": "Assinatura cancelada",
        "acesso_ate": u.assinatura_ativa_ate,
        "mensagem": f"Seu acesso continua ativo até {u.assinatura_ativa_ate or 'o fim do período'}.",
    }

# --- 2. ROTAS DE CONTAS E CATEGORIAS ---

@app.post("/contas/")
def criar_conta(conta: ContaCreate, db: Session = Depends(database.get_db)):
    # Validação específica de cartão: precisa dos dias de fechamento/vencimento
    if conta.modalidade == "cartao_credito":
        if not conta.dia_fechamento or not conta.dia_vencimento:
            raise HTTPException(
                status_code=400,
                detail="Cartão de crédito precisa de dia de fechamento e dia de vencimento.",
            )
        if not (1 <= conta.dia_fechamento <= 31) or not (1 <= conta.dia_vencimento <= 31):
            raise HTTPException(status_code=400, detail="Dias devem estar entre 1 e 31.")

    nova = models.ContaBancaria(
        nome=conta.nome,
        banco=conta.banco,
        tipo=conta.tipo,
        usuario_id=conta.usuario_id,
        modalidade=conta.modalidade or "corrente",
        dia_fechamento=conta.dia_fechamento if conta.modalidade == "cartao_credito" else None,
        dia_vencimento=conta.dia_vencimento if conta.modalidade == "cartao_credito" else None,
        limite=conta.limite if conta.modalidade == "cartao_credito" else None,
    )
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return nova

@app.get("/contas/{usuario_id}")
def listar_contas(usuario_id: int, db: Session = Depends(database.get_db)):
    return db.query(models.ContaBancaria).filter(models.ContaBancaria.usuario_id == usuario_id).all()

# --- CARTÃO DE CRÉDITO: faturas ---

@app.get("/cartoes/{cartao_id}/faturas-abertas")
def listar_faturas_abertas(cartao_id: int, usuario_id: int, db: Session = Depends(database.get_db)):
    """Lista faturas em aberto de um cartão, agrupadas por data de vencimento
    (data_caixa). Retorna a próxima fatura (saldo devedor mais antigo ainda não
    quitado) e também um resumo de todas as faturas com saldo != 0.

    Uma fatura é considerada 'quitada' quando a soma de todas as transações
    com a mesma data_caixa naquele cartão é == 0 (compras negativas canceladas
    pelo pagamento positivo da transferência interna)."""
    cartao = db.query(models.ContaBancaria).filter(
        models.ContaBancaria.id == cartao_id,
        models.ContaBancaria.usuario_id == usuario_id,
    ).first()
    if not cartao:
        raise HTTPException(status_code=404, detail="Cartão não encontrado")
    if cartao.modalidade != "cartao_credito":
        raise HTTPException(status_code=400, detail="Essa conta não é um cartão de crédito")

    # Agrupa por data_caixa (vencimento previsto) e soma os valores.
    # Compras entram como valor negativo, pagamento de fatura entra como positivo.
    resultados = (
        db.query(
            models.Transacao.data_caixa,
            func.sum(models.Transacao.valor).label("saldo"),
        )
        .filter(
            models.Transacao.conta_id == cartao_id,
            models.Transacao.usuario_id == usuario_id,
            models.Transacao.confirmado == True,
            models.Transacao.data_caixa.isnot(None),
        )
        .group_by(models.Transacao.data_caixa)
        .order_by(models.Transacao.data_caixa.asc())
        .all()
    )

    # Uma fatura "em aberto" é aquela cujo saldo não zera (fatura quitada = soma 0).
    # Como compras são negativas, uma fatura devedora tem saldo < 0.
    faturas = []
    for data_vencimento, saldo in resultados:
        if saldo is None or abs(saldo) < 0.01:
            continue
        faturas.append({
            "vencimento": data_vencimento,
            "valor": float(abs(saldo)),  # sempre mostra positivo pro MEI
        })

    return {
        "cartao_id": cartao_id,
        "cartao_nome": cartao.nome,
        "faturas": faturas,
        "proxima": faturas[0] if faturas else None,
    }


@app.post("/transacoes/pagar-fatura")
def pagar_fatura(dados: PagamentoFatura, db: Session = Depends(database.get_db)):
    """Registra o pagamento de uma fatura como um par atômico de transações
    marcadas como 'Transferência Interna':
      - saída (valor negativo) da conta corrente de origem
      - entrada (valor positivo) no cartão, zerando aquela fatura

    As duas transações compartilham o mesmo `tx_transferencia_id` (auto-FK)
    pra serem auditáveis como um par."""
    if dados.valor <= 0:
        raise HTTPException(status_code=400, detail="Valor do pagamento precisa ser maior que zero")

    cartao = db.query(models.ContaBancaria).filter(
        models.ContaBancaria.id == dados.cartao_id,
        models.ContaBancaria.usuario_id == dados.usuario_id,
    ).first()
    if not cartao or cartao.modalidade != "cartao_credito":
        raise HTTPException(status_code=400, detail="Cartão inválido")

    origem = db.query(models.ContaBancaria).filter(
        models.ContaBancaria.id == dados.conta_origem_id,
        models.ContaBancaria.usuario_id == dados.usuario_id,
    ).first()
    if not origem:
        raise HTTPException(status_code=400, detail="Conta de origem não encontrada")
    if origem.modalidade == "cartao_credito":
        raise HTTPException(
            status_code=400,
            detail="Você não pode pagar um cartão usando outro cartão — escolha uma conta corrente.",
        )

    data_iso = dados.data or date.today().isoformat()
    descricao = f"Pagamento fatura {cartao.nome}"

    # Cria as duas pernas da transferência. Ordem:
    # 1. Insere a saída, commit parcial pra ganhar um ID
    # 2. Insere a entrada usando o id da saída como tx_transferencia_id
    # 3. Atualiza a saída com o id da entrada
    # 4. Commit final
    try:
        saida = models.Transacao(
            data=data_iso,
            data_caixa=data_iso,  # conta corrente: competência = caixa
            descricao=descricao,
            valor=-abs(float(dados.valor)),
            categoria="Transferência Interna",
            tipo=cartao.tipo,  # mantém consistência PF/PJ com o cartão
            conta_id=origem.id,
            usuario_id=dados.usuario_id,
            confirmado=True,
        )
        db.add(saida)
        db.flush()  # gera o id sem fazer commit

        entrada = models.Transacao(
            data=data_iso,
            data_caixa=data_iso,  # pagamento é caixa imediato no cartão também
            descricao=descricao,
            valor=abs(float(dados.valor)),
            categoria="Transferência Interna",
            tipo=cartao.tipo,
            conta_id=cartao.id,
            usuario_id=dados.usuario_id,
            confirmado=True,
            tx_transferencia_id=saida.id,
        )
        db.add(entrada)
        db.flush()

        # Linka a saída na entrada (par bidirecional)
        saida.tx_transferencia_id = entrada.id

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao registrar pagamento: {e}")

    return {
        "status": "ok",
        "mensagem": f"Fatura de R$ {dados.valor:.2f} paga com sucesso",
        "saida_id": saida.id,
        "entrada_id": entrada.id,
    }

@app.get("/limites/")
def listar_limites(usuario_id: int, db: Session = Depends(database.get_db)):
    return db.query(models.LimiteCategoria).filter(models.LimiteCategoria.usuario_id == usuario_id).all()

@app.post("/limites/")
def definir_limite_manual(dados: LimiteCreate, db: Session = Depends(database.get_db)):
    limite_existente = db.query(models.LimiteCategoria).filter(
        models.LimiteCategoria.categoria == dados.categoria
    ).first()

    if limite_existente:
        limite_existente.valor_teto = dados.valor_teto
    else:
        novo_limite = models.LimiteCategoria(
            categoria=dados.categoria,
            valor_teto=dados.valor_teto,
            usuario_id=dados.usuario_id
        )
        db.add(novo_limite)

    db.commit()
    return {"status": "Meta atualizada com sucesso!"}

@app.delete("/limites/{limite_id}")
def excluir_limite(limite_id: int, db: Session = Depends(database.get_db)):
    limite = db.query(models.LimiteCategoria).filter(models.LimiteCategoria.id == limite_id).first()
    if not limite:
        raise HTTPException(status_code=404, detail="Teto não encontrado")
    db.delete(limite)
    db.commit()
    return {"status": "Teto removido"}

@app.get("/categorias")
def listar_categorias(db: Session = Depends(database.get_db)):
    return db.query(models.Categoria).order_by(models.Categoria.nome).all()

@app.post("/categorias")
def criar_categoria(cat: CategoriaCreate, db: Session = Depends(database.get_db)):
    if db.query(models.Categoria).filter(models.Categoria.nome == cat.nome).first():
        raise HTTPException(status_code=400, detail="Categoria já existe")
    nova = models.Categoria(nome=cat.nome, tipo=cat.tipo)
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return nova

@app.delete("/categorias/{categoria_id}")
def deletar_categoria(categoria_id: int, db: Session = Depends(database.get_db)):
    cat = db.query(models.Categoria).filter(models.Categoria.id == categoria_id).first()
    if cat:
        db.delete(cat)
        db.commit()
    return {"mensagem": "Categoria removida"}

# --- 3. O CORAÇÃO: INTELIGÊNCIA ARTIFICIAL (TEXTO E ÁUDIO) ---

def _contas_do_usuario_para_ia(db: Session, usuario_id: int) -> List[dict]:
    """Formata as contas do usuário como lista de dicts pra injetar no prompt da IA.
    Inclui modalidade pra IA conseguir distinguir conta corrente de cartão."""
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


def _validar_conta_do_usuario(db: Session, conta_id, usuario_id: int) -> Optional[int]:
    """Garante que o conta_id retornado pela IA realmente pertence ao usuário.
    Proteção defensiva: se a IA alucinar um id (ou um id de outro usuário),
    descartamos e caímos no fallback. Retorna o id válido ou None."""
    if conta_id is None:
        return None
    try:
        conta_id = int(conta_id)
    except (TypeError, ValueError):
        return None
    conta = db.query(models.ContaBancaria).filter(
        models.ContaBancaria.id == conta_id,
        models.ContaBancaria.usuario_id == usuario_id,
    ).first()
    return conta.id if conta else None


def processar_e_salvar_ia(dados_ia, db, usuario_id):
    """Lógica unificada para salvar o que a IA interpretou"""

    # CASO A: Definir Teto/Limite
    if dados_ia.get('natureza') == 'config_limite':
        limite = db.query(models.LimiteCategoria).filter(models.LimiteCategoria.categoria == dados_ia['categoria']).first()
        if limite:
            limite.valor_teto = dados_ia['valor']
        else:
            db.add(models.LimiteCategoria(categoria=dados_ia['categoria'], valor_teto=dados_ia['valor'], usuario_id=usuario_id))
        db.commit()
        return {"status": f"🎯 Meta de R$ {dados_ia['valor']:.2f} para {dados_ia['categoria']} salva!", "confirmado_automaticamente": True}

    # CASO B: Lançamento de Transação
    hoje = date.today().isoformat()

    # 1. Preferência: conta_id escolhido pela IA com contexto injetado.
    #    Sempre valida que a conta pertence ao usuário (defesa em profundidade).
    conta_id = _validar_conta_do_usuario(db, dados_ia.get('conta_id'), usuario_id)

    # 2. Fallback: se a IA não conseguiu escolher (ou escolheu inválido), tenta
    #    o matching fuzzy antigo por nome/banco. Mantido pra garantir que mesmo
    #    falhas de contexto do modelo não regridam o comportamento anterior.
    if conta_id is None and dados_ia.get('banco'):
        termo = dados_ia['banco'].lower()
        conta = db.query(models.ContaBancaria).filter(
            (models.ContaBancaria.nome.ilike(f"%{termo}%")) | (models.ContaBancaria.banco.ilike(f"%{termo}%")),
            models.ContaBancaria.tipo == dados_ia.get('tipo', 'PF'),
            models.ContaBancaria.usuario_id == usuario_id,
        ).first()
        if conta:
            conta_id = conta.id

    # Decide se vai direto ou quarentena
    vai_direto = True if (dados_ia.get('categoria') and dados_ia.get('categoria') != 'A Classificar' and conta_id) else False

    # Ajuste de sinal matemático
    valor_final = -abs(float(dados_ia.get('valor', 0))) if dados_ia.get('natureza') == 'saida' else abs(float(dados_ia.get('valor', 0)))

    nova_tx = models.Transacao(
        data=hoje,
        data_caixa=resolver_data_caixa(db, conta_id, hoje),
        descricao=dados_ia.get('descricao', 'Lançamento IA'),
        valor=valor_final,
        categoria=dados_ia.get('categoria', 'A Classificar'),
        tipo=dados_ia.get('tipo', 'PF'),
        conta_id=conta_id,
        usuario_id=usuario_id,
        confirmado=vai_direto
    )
    db.add(nova_tx)
    db.commit()

    msg = "⚡ Lançado direto!" if vai_direto else "⏳ Enviado para a Quarentena"
    return {"status": msg, "dados": dados_ia, "confirmado_automaticamente": vai_direto}

@app.post("/transacoes/ia")
def criar_transacao_texto(texto: str, usuario_id: int, db: Session = Depends(database.get_db)):
    contas_contexto = _contas_do_usuario_para_ia(db, usuario_id)
    dados_ia = ia_engine.processar_texto_ia(texto, contas=contas_contexto)
    return processar_e_salvar_ia(dados_ia, db, usuario_id)

@app.post("/transacoes/ia/audio")
async def criar_transacao_audio(usuario_id: int, file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    contas_contexto = _contas_do_usuario_para_ia(db, usuario_id)
    dados_ia = ia_engine.processar_audio_ia(temp_path, contas=contas_contexto)
    if os.path.exists(temp_path): os.remove(temp_path)

    return processar_e_salvar_ia(dados_ia, db, usuario_id=usuario_id)

# --- 4. GESTÃO DE TRANSAÇÕES (QUARENTENA, HISTÓRICO, EDIÇÃO) ---

@app.get("/transacoes/quarentena")
def listar_quarentena(usuario_id: int, db: Session = Depends(database.get_db)):
    q = db.query(models.Transacao).filter(models.Transacao.confirmado == False, models.Transacao.usuario_id == usuario_id).all()
    return {"transacoes": q}

@app.patch("/transacoes/{transacao_id}/confirmar")
def confirmar_transacao(transacao_id: int, dados: ConfirmacaoGasto, db: Session = Depends(database.get_db)):
    tx = db.query(models.Transacao).filter(models.Transacao.id == transacao_id).first()
    if not tx: raise HTTPException(status_code=404)
    for key, value in dados.dict().items(): setattr(tx, key, value)
    # Recalcula data_caixa com base na conta escolhida pelo usuário na revisão
    tx.data_caixa = resolver_data_caixa(db, dados.conta_id, dados.data)
    tx.confirmado = True
    db.commit()
    return {"status": "Sucesso"}

@app.put("/transacoes/{transacao_id}")
def editar_transacao_manual(transacao_id: int, dados: ConfirmacaoGasto, db: Session = Depends(database.get_db)):
    tx = db.query(models.Transacao).filter(models.Transacao.id == transacao_id).first()
    if not tx: raise HTTPException(status_code=404)
    tx.data = dados.data
    tx.descricao = dados.descricao
    tx.valor = dados.valor
    tx.categoria = dados.categoria
    tx.tipo = dados.tipo
    tx.conta_id = dados.conta_id
    tx.data_caixa = resolver_data_caixa(db, dados.conta_id, dados.data)
    db.commit()
    return {"status": "Editado com sucesso!"}

@app.delete("/transacoes/{transacao_id}")
def apagar_transacao(transacao_id: int, db: Session = Depends(database.get_db)):
    tx = db.query(models.Transacao).filter(models.Transacao.id == transacao_id).first()
    db.delete(tx)
    db.commit()
    return {"status": "Apagado"}

# --- HELPER: prefixo de data para filtro mensal/anual ---
def _prefixo_data(ano: Optional[int], mes: Optional[int]) -> Optional[str]:
    """Retorna o prefixo para LIKE ('YYYY-MM' ou 'YYYY'), ou None se sem filtro."""
    if not ano:
        return None
    if mes:
        return f"{ano:04d}-{mes:02d}"
    return f"{ano:04d}"

@app.get("/transacoes/historico")
def listar_historico(
    usuario_id: int,
    ano: Optional[int] = None,
    mes: Optional[int] = None,
    db: Session = Depends(database.get_db),
):
    q = db.query(models.Transacao).filter(
        models.Transacao.confirmado == True,
        models.Transacao.usuario_id == usuario_id,
    )
    prefixo = _prefixo_data(ano, mes)
    if prefixo:
        q = q.filter(models.Transacao.data.like(f"{prefixo}%"))
    return q.order_by(models.Transacao.id.desc()).all()

# --- 5. DASHBOARD E SISTEMA ---

@app.get("/dashboard/resumo")
def resumo_financeiro(
    usuario_id: int,
    ano: Optional[int] = None,
    mes: Optional[int] = None,
    db: Session = Depends(database.get_db),
):
    prefixo = _prefixo_data(ano, mes)

    def calc(tipo, sinal):
        # Exclui "Transferência Interna" do cálculo: movimentações entre contas
        # do próprio usuário (ex: pagamento de fatura de cartão) não são nem
        # receita nem despesa real — inflaria os cards da sidebar.
        q = db.query(func.sum(models.Transacao.valor)).filter(
            models.Transacao.tipo == tipo, models.Transacao.confirmado == True,
            models.Transacao.usuario_id == usuario_id,
            (models.Transacao.valor > 0 if sinal == "+" else models.Transacao.valor < 0),
            models.Transacao.categoria != "Transferência Interna",
        )
        if prefixo:
            q = q.filter(models.Transacao.data.like(f"{prefixo}%"))
        return q.scalar() or 0

    rpj, dpj = calc("PJ", "+"), calc("PJ", "-")
    rpf, dpf = calc("PF", "+"), calc("PF", "-")

    return {
        "pj": {"receitas": f"R$ {rpj:.2f}", "despesas": f"R$ {abs(dpj):.2f}", "saldo": f"R$ {rpj+dpj:.2f}"},
        "pf": {"receitas": f"R$ {rpf:.2f}", "despesas": f"R$ {abs(dpf):.2f}", "saldo": f"R$ {rpf+dpf:.2f}"}
    }

@app.delete("/sistema/resetar-transacoes")
def resetar_transacoes(usuario_id: int, db: Session = Depends(database.get_db)):
    db.query(models.Transacao).filter(models.Transacao.usuario_id == usuario_id).delete()
    db.commit()
    return {"status": "Transações zeradas!"}

@app.delete("/sistema/recriar-banco")
def recriar_banco():
    models.Base.metadata.drop_all(bind=database.engine)
    models.Base.metadata.create_all(bind=database.engine)
    return {"status": "Banco limpo!"}

# --- ROTAS RESTAURADAS: LOTE (CSV) E LIMPEZA DE QUARENTENA ---

@app.delete("/sistema/limpar-quarentena")
def limpar_quarentena(usuario_id: int, db: Session = Depends(database.get_db)):
    db.query(models.Transacao).filter(models.Transacao.confirmado == False, models.Transacao.usuario_id == usuario_id).delete()
    db.commit()
    return {"mensagem": "Quarentena esvaziada!"}

def _normalizar_data_iso(data_str: str) -> str:
    """Converte datas comuns de extratos bancários para ISO 'YYYY-MM-DD'.
    Aceita: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, DD/MM/YY, YYYY/MM/DD.
    Se não reconhecer, devolve a string original (não perde o dado)."""
    if not data_str:
        return data_str
    s = str(data_str).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return data_str

@app.post("/transacoes/lote")
def importar_lote_csv(lote: LoteTransacoes, db: Session = Depends(database.get_db)):
    conta = db.query(models.ContaBancaria).filter(models.ContaBancaria.id == lote.conta_id).first()
    tipo_da_conta = conta.tipo if conta else "PF"

    for t in lote.transacoes:
        # Tenta lembrar a categoria de um gasto igual no passado
        transacao_antiga = db.query(models.Transacao).filter(
            models.Transacao.descricao == t.descricao,
            models.Transacao.confirmado == True
        ).order_by(models.Transacao.id.desc()).first()

        categoria_sugerida = transacao_antiga.categoria if transacao_antiga else "A Classificar"
        data_competencia = _normalizar_data_iso(t.data)

        nova_tx = models.Transacao(
            data=data_competencia,
            data_caixa=resolver_data_caixa(db, lote.conta_id, data_competencia),
            descricao=t.descricao,
            valor=t.valor,
            categoria=categoria_sugerida,
            tipo=tipo_da_conta,
            conta_id=lote.conta_id,
            usuario_id=lote.usuario_id,
            confirmado=False
        )
        db.add(nova_tx)

    db.commit()
    return {"mensagem": f"{len(lote.transacoes)} transações enviadas para a Quarentena!"}

@app.get("/")
def home(): return {"status": "online"}