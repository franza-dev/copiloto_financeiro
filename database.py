import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Carrega as variáveis de segurança do arquivo .env
load_dotenv()

# Pega a URL do banco que colocamos no .env
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Cria o motor de conexão com o banco
engine = create_engine(SQLALCHEMY_DATABASE_URL)

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