"""
Guido — Asaas Payment Handler
Recebe webhooks do Asaas quando um pagamento é confirmado, cria a conta
do usuário automaticamente, e envia as credenciais via WhatsApp.

Fluxo:
  1. MEI clica "Assinar" no site → vai pro checkout do Asaas
  2. Asaas coleta nome, email, CPF, cartão
  3. Primeira cobrança aprovada → Asaas manda webhook pra cá
  4. Nós criamos a conta no Guido com senha aleatória
  5. Mandamos as credenciais via WhatsApp pro número do cliente
  6. Meses seguintes: Asaas cobra automaticamente
"""
import os
import string
import secrets
import requests as http_requests
from datetime import date, timedelta
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
import hashlib

import models
import database

router = APIRouter(prefix="/asaas", tags=["asaas"])

ASAAS_API_KEY = os.getenv("ASAAS_API_KEY", "")
ASAAS_API_URL = "https://api.asaas.com/v3"


# ==========================================
# HELPERS
# ==========================================

def _gerar_senha(tamanho: int = 8) -> str:
    """Gera uma senha aleatória legível (sem caracteres ambíguos)."""
    # Remove caracteres confusos: 0/O, 1/l/I
    alfabeto = string.ascii_letters + string.digits
    alfabeto = alfabeto.replace("0", "").replace("O", "").replace("l", "").replace("I", "").replace("1", "")
    return ''.join(secrets.choice(alfabeto) for _ in range(tamanho))


def _hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()


def _normalizar_telefone(telefone: str) -> str:
    """Remove tudo que não é dígito e garante prefixo 55."""
    apenas_digitos = ''.join(c for c in str(telefone) if c.isdigit())
    if not apenas_digitos.startswith("55"):
        apenas_digitos = "55" + apenas_digitos
    return apenas_digitos


def _buscar_cliente_asaas(customer_id: str) -> dict:
    """Busca dados completos do cliente na API do Asaas."""
    try:
        resp = http_requests.get(
            f"{ASAAS_API_URL}/customers/{customer_id}",
            headers={"access_token": ASAAS_API_KEY},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"[Asaas] Erro ao buscar cliente {customer_id}: {e}")
    return {}


def _enviar_whatsapp(telefone: str, texto: str):
    """Envia mensagem via Evolution API (mesma config do whatsapp_handler)."""
    evo_url = os.getenv("EVOLUTION_API_URL", "")
    evo_key = os.getenv("EVOLUTION_API_KEY", "")
    evo_instance = os.getenv("EVOLUTION_INSTANCE", "Guido")
    if not evo_url or not evo_key:
        print(f"[Asaas] Evolution API não configurada, não enviou WhatsApp")
        return
    try:
        http_requests.post(
            f"{evo_url}/message/sendText/{evo_instance}",
            json={"number": telefone, "text": texto},
            headers={"apikey": evo_key, "Content-Type": "application/json"},
            timeout=10,
        )
        print(f"[Asaas] WhatsApp enviado pra {telefone}")
    except Exception as e:
        print(f"[Asaas] Erro ao enviar WhatsApp: {e}")


# ==========================================
# WEBHOOK
# ==========================================

@router.post("/webhook")
async def webhook_asaas(request: Request, db: Session = Depends(database.get_db)):
    """Recebe webhooks do Asaas para eventos de pagamento."""
    try:
        body = await request.json()
    except Exception:
        return {"status": "ok"}

    event = body.get("event", "")
    payment = body.get("payment", {})

    print(f"[Asaas] Webhook recebido: event={event} payment_id={payment.get('id')}")

    # Só processa pagamentos confirmados/recebidos
    if event not in ("PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"):
        return {"status": "ignored", "event": event}

    # Filtra só pagamentos do Guido (R$ 19/mês).
    # Outros produtos da conta Asaas (1k, 2k, 2.5k) são ignorados.
    valor = payment.get("value", 0)
    if valor != 19 and valor != 19.0:
        print(f"[Asaas] Pagamento ignorado: valor R$ {valor} não é do Guido (R$ 19)")
        return {"status": "ignored", "detail": f"valor {valor} não é Guido"}

    customer_id = payment.get("customer")
    if not customer_id:
        return {"status": "error", "detail": "sem customer_id"}

    # Busca dados do cliente no Asaas
    cliente = _buscar_cliente_asaas(customer_id)
    if not cliente:
        return {"status": "error", "detail": "cliente não encontrado no Asaas"}

    nome = cliente.get("name", "")
    email = (cliente.get("email") or "").strip().lower()
    telefone_raw = cliente.get("mobilePhone") or cliente.get("phone") or ""
    telefone = _normalizar_telefone(telefone_raw) if telefone_raw else ""

    if not email:
        print(f"[Asaas] Cliente {customer_id} sem email — não cria conta")
        return {"status": "error", "detail": "cliente sem email"}

    # Calcula data de acesso: 30 dias a partir de hoje
    acesso_ate = (date.today() + timedelta(days=30)).isoformat()

    # Busca subscription_id (se veio de assinatura recorrente)
    subscription_id = payment.get("subscription") or None

    # Verifica se já existe conta com esse email
    usuario_existente = db.query(models.Usuario).filter(
        models.Usuario.email == email
    ).first()

    if usuario_existente:
        # Usuário já existe — atualiza dados da assinatura
        if telefone and not usuario_existente.telefone:
            usuario_existente.telefone = telefone
        usuario_existente.assinatura_cliente_asaas = customer_id
        if subscription_id:
            usuario_existente.assinatura_id_asaas = subscription_id
        usuario_existente.assinatura_ativa_ate = acesso_ate
        db.commit()
        print(f"[Asaas] Usuário {email} já existe (id={usuario_existente.id}) — assinatura renovada até {acesso_ate}")

        # Manda confirmação se tiver WhatsApp
        if telefone:
            _enviar_whatsapp(telefone, (
                f"Oi, {usuario_existente.nome.split()[0]}! 🎉\n\n"
                "Pagamento confirmado. Sua assinatura do Guido tá ativa "
                f"até *{acesso_ate}*!\n\n"
                "Acesse seu painel:\n"
                "👉 app.chamaoguido.com\n\n"
                "E pode me mandar seus gastos aqui pelo WhatsApp também. 🤓"
            ))
        return {"status": "ok", "detail": "assinatura renovada"}

    # Cria nova conta
    senha_raw = _gerar_senha(8)
    novo_usuario = models.Usuario(
        nome=nome,
        email=email,
        senha_hash=_hash_senha(senha_raw),
        telefone=telefone if telefone else None,
        assinatura_cliente_asaas=customer_id,
        assinatura_id_asaas=subscription_id,
        assinatura_ativa_ate=acesso_ate,
    )

    try:
        db.add(novo_usuario)
        db.commit()
        db.refresh(novo_usuario)
        print(f"[Asaas] Conta criada: {email} (id={novo_usuario.id})")
    except Exception as e:
        db.rollback()
        print(f"[Asaas] Erro ao criar conta: {e}")
        return {"status": "error", "detail": str(e)}

    # Envia credenciais via WhatsApp
    if telefone:
        _enviar_whatsapp(telefone, (
            f"Bem-vindo ao Guido, {nome.split()[0]}! 🎉\n\n"
            "Sua conta foi criada. Aqui estão seus dados de acesso:\n\n"
            f"📧 Email: {email}\n"
            f"🔑 Senha: {senha_raw}\n\n"
            "Acesse seu painel financeiro:\n"
            "👉 app.chamaoguido.com\n\n"
            "E a partir de agora, pode me mandar seus gastos aqui "
            "pelo WhatsApp! Exemplo:\n"
            '• "gastei 80 em esmalte"\n'
            '• "recebi 500 do cliente"\n'
            '• "quanto gastei esse mês?"\n\n'
            "Eu sou o Guido, seu braço direito financeiro. 🤓"
        ))

    return {"status": "ok", "usuario_id": novo_usuario.id}


@router.get("/status")
def asaas_status():
    """Health check do módulo Asaas."""
    return {
        "status": "online",
        "api_key_configurada": bool(ASAAS_API_KEY),
    }
