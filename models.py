from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    email = Column(String, unique=True)
    contas = relationship("ContaBancaria", back_populates="dono")

class ContaBancaria(Base):
    __tablename__ = "contas"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String) # Ex: Nubank Empresa
    banco = Column(String) # Ex: Nubank
    tipo = Column(String) # PF ou PJ
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    
    dono = relationship("Usuario", back_populates="contas")
    transacoes = relationship("Transacao", back_populates="conta")

class Transacao(Base):
    __tablename__ = "transacoes"
    id = Column(Integer, primary_key=True, index=True)
    data = Column(String, default="") # <-- NOVA COLUNA DE DATA ADICIONADA AQUI
    descricao = Column(String)
    valor = Column(Float)
    categoria = Column(String)
    tipo = Column(String) # PF ou PJ
    confirmado = Column(Boolean, default=False)
    
    # AGORA O GASTO É LIGADO A UMA CONTA ESPECÍFICA
    conta_id = Column(Integer, ForeignKey("contas.id"))
    conta = relationship("ContaBancaria", back_populates="transacoes")
    
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))