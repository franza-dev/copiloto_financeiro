from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
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

# Migração rápida para colunas essenciais
with database.engine.connect() as _conn:
    try:
        _conn.execute(text("ALTER TABLE usuarios ADD COLUMN senha_hash VARCHAR"))
        _conn.commit()
    except: pass # Já existe

app = FastAPI(
    title="Guido API",
    description="Seu braço direito pra separar o dinheiro da casa do dinheiro do negócio. chamaoguido.com.br",
    version="1.0.0",
)

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
    tipo: str
    usuario_id: int

class RegistroUsuario(BaseModel):
    nome: str
    email: str
    senha: str

class LoginUsuario(BaseModel):
    email: str
    senha: str

class CategoriaCreate(BaseModel):
    nome: str
    tipo: str = "Ambos"

# --- 1. ROTAS DE AUTENTICAÇÃO ---

@app.post("/auth/registrar")
def registrar_usuario(dados: RegistroUsuario, db: Session = Depends(database.get_db)):
    if db.query(models.Usuario).filter(models.Usuario.email == dados.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    novo = models.Usuario(nome=dados.nome, email=dados.email, senha_hash=hash_senha(dados.senha))
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

# --- 2. ROTAS DE CONTAS E CATEGORIAS ---

@app.post("/contas/")
def criar_conta(conta: ContaCreate, db: Session = Depends(database.get_db)):
    nova = models.ContaBancaria(nome=conta.nome, banco=conta.banco, tipo=conta.tipo, usuario_id=conta.usuario_id)
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return nova

@app.get("/contas/{usuario_id}")
def listar_contas(usuario_id: int, db: Session = Depends(database.get_db)):
    return db.query(models.ContaBancaria).filter(models.ContaBancaria.usuario_id == usuario_id).all()

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
    conta_id = None
    
    # Busca conta por nome ou banco
    if dados_ia.get('banco'):
        termo = dados_ia['banco'].lower()
        conta = db.query(models.ContaBancaria).filter(
            (models.ContaBancaria.nome.ilike(f"%{termo}%")) | (models.ContaBancaria.banco.ilike(f"%{termo}%")),
            models.ContaBancaria.tipo == dados_ia.get('tipo', 'PF')
        ).first()
        if conta: conta_id = conta.id

    # Decide se vai direto ou quarentena
    vai_direto = True if (dados_ia.get('categoria') and conta_id) else False
    
    # Ajuste de sinal matemático
    valor_final = -abs(float(dados_ia.get('valor', 0))) if dados_ia.get('natureza') == 'saida' else abs(float(dados_ia.get('valor', 0)))

    nova_tx = models.Transacao(
        data=hoje,
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
    dados_ia = ia_engine.processar_texto_ia(texto)
    return processar_e_salvar_ia(dados_ia, db, usuario_id)

@app.post("/transacoes/ia/audio")
async def criar_transacao_audio(usuario_id: int, file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    dados_ia = ia_engine.processar_audio_ia(temp_path)
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
        q = db.query(func.sum(models.Transacao.valor)).filter(
            models.Transacao.tipo == tipo, models.Transacao.confirmado == True,
            models.Transacao.usuario_id == usuario_id,
            (models.Transacao.valor > 0 if sinal == "+" else models.Transacao.valor < 0)
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

        nova_tx = models.Transacao(
            data=_normalizar_data_iso(t.data),
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