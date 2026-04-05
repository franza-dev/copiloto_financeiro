import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Carrega as variáveis de segurança do arquivo .env
load_dotenv()

# Pega a URL do banco que colocamos no .env
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Cria o motor de conexão com o banco.
#
# Configuração específica pra Neon (Postgres serverless):
# - pool_pre_ping=True: faz um SELECT 1 antes de cada uso pra detectar
#   conexões que o Neon derrubou por ociosidade. Sem isso, o pool devolve
#   uma conexão morta e a query estoura com "SSL connection has been closed
#   unexpectedly", aparecendo pro usuário como "API offline".
# - pool_recycle=280: recicla conexões após 280s (<5min) proativamente, já
#   que o Neon tende a cortar conexões ociosas nessa janela.
# - pool_size=5 / max_overflow=10: limites conservadores — o Neon free tier
#   tem quota de conexões simultâneas e o app é pequeno.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=5,
    max_overflow=10,
)

# Cria a "fábrica" de sessões (as conversas com o banco)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe base que vamos usar para criar nossas tabelas
Base = declarative_base()

# Função que abre e fecha a conexão a cada pedido do usuário
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()