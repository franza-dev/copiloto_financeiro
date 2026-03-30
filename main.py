from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List
from datetime import datetime
import models, database, ia_engine

# 1. INICIALIZAÇÃO
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Copiloto Financeiro API")

# --- MODELOS DE DADOS (Envelopes) ---

class ConfirmacaoGasto(BaseModel):
    data: str
    descricao: str
    valor: float
    categoria: str
    tipo: str
    conta_id: int

class TransacaoImportada(BaseModel):
    data: str
    descricao: str
    valor: float

class LoteTransacoes(BaseModel):
    conta_id: int
    transacoes: List[TransacaoImportada]

class ContaCreate(BaseModel):
    nome: str
    banco: str
    tipo: str
    usuario_id: int

# --- ROTAS DE UTILIZADORES ---

@app.post("/usuarios/")
def criar_usuario(nome: str, email: str, db: Session = Depends(database.get_db)):
    usuario_existente = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Este email já está registrado!")
    novo_usuario = models.Usuario(nome=nome, email=email)
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return {"mensagem": "Utilizador criado com sucesso!", "usuario": novo_usuario}

# --- ROTAS DE CONTAS BANCÁRIAS ---

@app.post("/contas/")
def criar_conta(conta: ContaCreate, db: Session = Depends(database.get_db)):
    nova_conta = models.ContaBancaria(
        nome=conta.nome,
        banco=conta.banco,
        tipo=conta.tipo,
        usuario_id=conta.usuario_id
    )
    db.add(nova_conta)
    db.commit()
    db.refresh(nova_conta)
    return {"mensagem": "Conta criada com sucesso!", "conta": nova_conta}

@app.get("/contas/{usuario_id}")
def listar_contas(usuario_id: int, db: Session = Depends(database.get_db)):
    contas = db.query(models.ContaBancaria).filter(models.ContaBancaria.usuario_id == usuario_id).all()
    return contas

# --- ROTAS DE INTELIGÊNCIA ARTIFICIAL ---

@app.post("/transacoes/ia")
def criar_transacao_ia(texto: str, usuario_id: int, db: Session = Depends(database.get_db)):
    dados_ia = ia_engine.processar_texto_com_gemini(texto)
    hoje = datetime.now().strftime("%d/%m/%Y") # Pega a data de hoje automaticamente
    
    nova_transacao = models.Transacao(
        data=hoje,
        descricao=dados_ia['descricao'],
        valor=dados_ia['valor'],
        categoria=dados_ia['categoria'],
        tipo=dados_ia['tipo'],
        usuario_id=usuario_id,
        confirmado=False 
    )
    db.add(nova_transacao)
    db.commit()
    db.refresh(nova_transacao)
    return {"status": "Processado pela IA", "dados": dados_ia, "id": nova_transacao.id}

# --- ROTAS DE GESTÃO E QUARENTENA ---

@app.get("/transacoes/quarentena")
def listar_pendentes(db: Session = Depends(database.get_db)):
    pendentes = db.query(models.Transacao).filter(models.Transacao.confirmado == False).all()
    return {"total_pendentes": len(pendentes), "transacoes": pendentes}

@app.patch("/transacoes/{transacao_id}/confirmar")
def confirmar_transacao(transacao_id: int, dados: ConfirmacaoGasto, db: Session = Depends(database.get_db)):
    transacao = db.query(models.Transacao).filter(models.Transacao.id == transacao_id).first()
    if not transacao:
        raise HTTPException(status_code=404, detail="Transação não encontrada!")
    
    transacao.data = dados.data
    transacao.descricao = dados.descricao
    transacao.valor = dados.valor
    transacao.categoria = dados.categoria
    transacao.tipo = dados.tipo
    transacao.conta_id = dados.conta_id
    transacao.confirmado = True
    
    db.commit()
    return {"mensagem": "Transação validada com sucesso! ✅"}

# --- ROTA DE EDIÇÃO MANUAL ---

@app.put("/transacoes/{transacao_id}")
def editar_transacao_manual(transacao_id: int, dados: ConfirmacaoGasto, db: Session = Depends(database.get_db)):
    transacao = db.query(models.Transacao).filter(models.Transacao.id == transacao_id).first()
    if not transacao:
        raise HTTPException(status_code=404, detail="Transação não encontrada!")
    
    transacao.data = dados.data
    transacao.descricao = dados.descricao
    transacao.valor = dados.valor
    transacao.categoria = dados.categoria
    transacao.tipo = dados.tipo
    transacao.conta_id = dados.conta_id
    
    db.commit()
    return {"mensagem": "Transação editada com sucesso!"}

@app.delete("/transacoes/{transacao_id}")
def apagar_transacao(transacao_id: int, db: Session = Depends(database.get_db)):
    transacao = db.query(models.Transacao).filter(models.Transacao.id == transacao_id).first()
    if not transacao:
        raise HTTPException(status_code=404, detail="Transação não encontrada!")
    
    db.delete(transacao)
    db.commit()
    return {"mensagem": f"Transação {transacao_id} eliminada com sucesso! 🗑️"}

@app.post("/transacoes/lote")
def importar_lote_csv(lote: LoteTransacoes, db: Session = Depends(database.get_db)):
    conta = db.query(models.ContaBancaria).filter(models.ContaBancaria.id == lote.conta_id).first()
    tipo_da_conta = conta.tipo if conta else "PF" 

    for t in lote.transacoes:
        
        # --- MÁGICA DA MEMÓRIA AUTOMÁTICA 🧠 ---
        # O sistema procura no banco se você já confirmou um gasto com essa exata descrição no passado
        transacao_antiga = db.query(models.Transacao).filter(
            models.Transacao.descricao == t.descricao,
            models.Transacao.confirmado == True
        ).order_by(models.Transacao.id.desc()).first()

        # Se ele lembrar, ele copia a categoria. Se for a primeira vez, ele deixa "A Classificar"
        categoria_sugerida = transacao_antiga.categoria if transacao_antiga else "A Classificar"
        # ---------------------------------------

        nova_tx = models.Transacao(
            data=t.data,
            descricao=t.descricao,
            valor=t.valor,
            categoria=categoria_sugerida, # <-- Agora ele usa a memória aqui!
            tipo=tipo_da_conta,
            conta_id=lote.conta_id,
            usuario_id=1,
            confirmado=False
        )
        db.add(nova_tx)
    
    db.commit()
    return {"mensagem": f"{len(lote.transacoes)} transações enviadas para a Quarentena!"}
# --- ROTA DE EXTRATO (HISTÓRICO) ---

@app.get("/transacoes/historico")
def listar_historico(db: Session = Depends(database.get_db)):
    historico = db.query(models.Transacao).filter(models.Transacao.confirmado == True).order_by(models.Transacao.id.desc()).all()
    return historico

# --- ROTA DE DASHBOARD ---

@app.get("/dashboard/resumo")
def ver_resumo_financeiro(db: Session = Depends(database.get_db)):
    # O Pulo do Gato 2.0: Ignorar APENAS a categoria exata "Transferência Interna"
    filtro_categoria = ~models.Transacao.categoria.ilike('Transferência Interna')

    # Cálculos PJ
    receitas_pj = db.query(func.sum(models.Transacao.valor)).filter(
        models.Transacao.tipo == "PJ", 
        models.Transacao.confirmado == True, 
        models.Transacao.valor > 0,
        filtro_categoria
    ).scalar() or 0
    
    despesas_pj = db.query(func.sum(models.Transacao.valor)).filter(
        models.Transacao.tipo == "PJ", 
        models.Transacao.confirmado == True, 
        models.Transacao.valor < 0,
        filtro_categoria
    ).scalar() or 0

    # Cálculos PF
    receitas_pf = db.query(func.sum(models.Transacao.valor)).filter(
        models.Transacao.tipo == "PF", 
        models.Transacao.confirmado == True, 
        models.Transacao.valor > 0,
        filtro_categoria
    ).scalar() or 0
    
    despesas_pf = db.query(func.sum(models.Transacao.valor)).filter(
        models.Transacao.tipo == "PF", 
        models.Transacao.confirmado == True, 
        models.Transacao.valor < 0,
        filtro_categoria
    ).scalar() or 0
    
    return {
        "pj": {
            "receitas": f"R$ {receitas_pj:.2f}",
            "despesas": f"R$ {abs(despesas_pj):.2f}",
            "saldo": f"R$ {(receitas_pj + despesas_pj):.2f}"
        },
        "pf": {
            "receitas": f"R$ {receitas_pf:.2f}",
            "despesas": f"R$ {abs(despesas_pf):.2f}",
            "saldo": f"R$ {(receitas_pf + despesas_pf):.2f}"
        }
    }

# --- ROTAS DE MANUTENÇÃO E ZONA DE PERIGO ---

@app.delete("/sistema/resetar-transacoes")
def resetar_todas_transacoes(db: Session = Depends(database.get_db)):
    db.query(models.Transacao).delete()
    db.commit()
    return {"mensagem": "Todas as transações foram apagadas com sucesso! Sistema zerado."}

@app.delete("/sistema/limpar-quarentena")
def limpar_quarentena(db: Session = Depends(database.get_db)):
    # Deleta apenas o que ainda NÃO foi confirmado
    db.query(models.Transacao).filter(models.Transacao.confirmado == False).delete()
    db.commit()
    return {"mensagem": "Quarentena esvaziada!"}

@app.delete("/sistema/recriar-banco")
def recriar_banco(db: Session = Depends(database.get_db)):
    # Formata o banco inteiro para aceitar novas colunas
    models.Base.metadata.drop_all(bind=database.engine)
    models.Base.metadata.create_all(bind=database.engine)
    return {"mensagem": "Banco recriado com sucesso!"}

@app.get("/")
def home():
    return {"status": "online", "msg": "Motor pronto!"}