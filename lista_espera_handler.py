"""
Guido — Lista de Espera Handler
Coleta inscrições da landing page pré-lançamento (chamaoguido.com/lista).

Endpoints:
  POST /lista/inscrever         → público, sem auth
  GET  /lista/inscritos         → admin-only (admin_id=1)
  POST /lista/marcar-notificado → admin-only, marca que uma inscrição
                                    já foi contactada sobre o lançamento
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

import models
import database

router = APIRouter(prefix="/lista", tags=["lista-espera"])

ADMIN_IDS = [1]


# ==========================================
# SCHEMAS
# ==========================================

class InscricaoInput(BaseModel):
    nome: str
    email: str
    telefone: Optional[str] = None
    desafio: Optional[str] = None


# ==========================================
# ENDPOINTS
# ==========================================

@router.post("/inscrever")
def inscrever(payload: InscricaoInput, db: Session = Depends(database.get_db)):
    """Registra um interessado na lista de espera.

    Se o email já existe, atualiza os dados (upsert) em vez de falhar.
    """
    nome = payload.nome.strip()
    email = payload.email.strip().lower()
    telefone = (payload.telefone or "").strip() or None
    desafio = (payload.desafio or "").strip() or None

    if not nome:
        raise HTTPException(status_code=400, detail="Nome é obrigatório")
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Email inválido")

    existente = db.query(models.ListaEspera).filter(models.ListaEspera.email == email).first()

    if existente:
        existente.nome = nome
        existente.telefone = telefone
        existente.desafio = desafio
        db.commit()
        return {"ok": True, "acao": "atualizado", "id": existente.id}

    nova = models.ListaEspera(
        nome=nome,
        email=email,
        telefone=telefone,
        desafio=desafio,
        criado_em=datetime.utcnow(),
        notificado=False,
    )
    db.add(nova)
    db.commit()
    db.refresh(nova)

    print(f"[Lista de Espera] Nova inscrição: {email} — {nome}")
    return {"ok": True, "acao": "criado", "id": nova.id}


@router.get("/inscritos")
def listar_inscritos(admin_id: int, db: Session = Depends(database.get_db)):
    """Lista todos os inscritos. Só admin (admin_id=1)."""
    if admin_id not in ADMIN_IDS:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")

    inscritos = (
        db.query(models.ListaEspera)
        .order_by(models.ListaEspera.criado_em.desc())
        .all()
    )
    return [
        {
            "id": i.id,
            "nome": i.nome,
            "email": i.email,
            "telefone": i.telefone,
            "desafio": i.desafio,
            "criado_em": i.criado_em.isoformat() if i.criado_em else None,
            "notificado": i.notificado,
        }
        for i in inscritos
    ]


@router.post("/marcar-notificado/{inscrito_id}")
def marcar_notificado(inscrito_id: int, admin_id: int, db: Session = Depends(database.get_db)):
    """Marca uma inscrição como já notificada sobre o lançamento."""
    if admin_id not in ADMIN_IDS:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")

    inscrito = db.query(models.ListaEspera).filter(models.ListaEspera.id == inscrito_id).first()
    if not inscrito:
        raise HTTPException(status_code=404, detail="Não encontrado")

    inscrito.notificado = not inscrito.notificado  # toggle
    db.commit()
    return {"ok": True, "notificado": inscrito.notificado}
