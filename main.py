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