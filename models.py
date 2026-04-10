from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, Text, DateTime
from sqlalchemy.orm import relationship
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    email = Column(String, unique=True)
    senha_hash = Column(String, nullable=True)
    telefone = Column(String, nullable=True, unique=True)  # +5511999999999 — vincula WhatsApp

    # Assinatura (Asaas)
    assinatura_cliente_asaas = Column(String, nullable=True)  # customer_id no Asaas
    assinatura_id_asaas = Column(String, nullable=True)       # subscription_id no Asaas
    assinatura_ativa_ate = Column(String, nullable=True)       # YYYY-MM-DD — acesso até essa data

    contas = relationship("ContaBancaria", back_populates="dono")

class ContaBancaria(Base):
    __tablename__ = "contas"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String) # Ex: Nubank Empresa
    banco = Column(String) # Ex: Nubank
    tipo = Column(String) # PF ou PJ
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))

    # --- Cartão de crédito (fase 1) ---
    # modalidade='corrente' (default, débito/pix/transferência — saldo imediato)
    # modalidade='cartao_credito' (compras hoje, fatura paga depois)
    modalidade = Column(String, default="corrente")
    dia_fechamento = Column(Integer, nullable=True)  # 1..31, só se cartão
    dia_vencimento = Column(Integer, nullable=True)  # 1..31, só se cartão
    limite = Column(Float, nullable=True)            # opcional, só se cartão

    dono = relationship("Usuario", back_populates="contas")
    transacoes = relationship("Transacao", back_populates="conta")

class Transacao(Base):
    __tablename__ = "transacoes"
    id = Column(Integer, primary_key=True, index=True)
    # `data` é a DATA DE COMPETÊNCIA: quando a despesa foi feita.
    # Usada nos filtros de período e nos gráficos de categoria — o MEI pensa
    # em "gastei X esse mês" por data de compra, não por data de pagamento.
    data = Column(String, default="")
    descricao = Column(String)
    valor = Column(Float)
    categoria = Column(String)
    tipo = Column(String) # PF ou PJ
    confirmado = Column(Boolean, default=False)

    # --- Datas separadas competência/caixa (fase 1) ---
    # `data_caixa` é quando o dinheiro sai DE VERDADE da conta corrente.
    # Para conta corrente: data_caixa == data.
    # Para cartão: data_caixa = próximo vencimento depois do fechamento
    # imediatamente posterior à `data` da compra.
    data_caixa = Column(String, nullable=True)

    # --- Transferências internas (fase 2, mas o campo nasce aqui p/ evitar
    #     nova migration depois). Pares de transações com o mesmo valor nesse
    #     campo representam transferência de A pra B (ex: pagamento de fatura).
    tx_transferencia_id = Column(Integer, nullable=True)

    # AGORA O GASTO É LIGADO A UMA CONTA ESPECÍFICA
    conta_id = Column(Integer, ForeignKey("contas.id"))
    conta = relationship("ContaBancaria", back_populates="transacoes")

    usuario_id = Column(Integer, ForeignKey("usuarios.id"))

class Categoria(Base):
    __tablename__ = "categorias"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True)
    tipo = Column(String, default="Ambos")  # PF, PJ, ou Ambos
    
class LimiteCategoria(Base):
    __tablename__ = "limites_categorias"
    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(String, unique=True, index=True)
    valor_teto = Column(Float)
    usuario_id = Column(Integer)


class BlogPost(Base):
    """Posts publicados no blog do site (chamaoguido.com/blog).

    Alimentado pelo projeto Marketing_guido via POST /api/blog/publicar com
    header X-API-Key. O agente envia o markdown bruto + frontmatter; o backend
    converte pra HTML e armazena os dois (md original como fonte da verdade,
    html como cache pra renderização rápida).
    """
    __tablename__ = "blog_posts"
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    meta_description = Column(String, nullable=True)
    categoria = Column(String, nullable=True)
    keywords = Column(String, nullable=True)  # CSV
    autor = Column(String, nullable=True, default="Equipe Guido")
    conteudo_md = Column(Text, nullable=False)
    conteudo_html = Column(Text, nullable=False)
    frontmatter_json = Column(Text, nullable=True)  # JSON serializado do YAML original
    publicado_em = Column(DateTime, nullable=False)
    status = Column(String, default="publicado")  # publicado | rascunho
