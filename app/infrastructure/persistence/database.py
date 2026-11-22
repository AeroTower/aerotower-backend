from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import DATABASE_URL


def opcoes_do_engine(url: str) -> dict:
    """Opcoes do create_engine que dependem do banco.

    SQLite: `check_same_thread` desligado, porque a thread do MQTT e a do
    FastAPI usam o mesmo banco. (So existe no SQLite; passar para o driver
    do Postgres derruba a aplicacao no start.)

    Postgres: o Azure fecha conexoes paradas. Sem `pool_pre_ping`, a
    primeira requisicao depois de um tempo ocioso pega uma conexao morta do
    pool e da erro 500. Com ele, o SQLAlchemy testa a conexao antes de usar
    e abre outra se precisar. `pool_recycle` renova conexoes com mais de
    30 min, antes que o servidor as derrube.
    """
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True, "pool_recycle": 1800}


engine = create_engine(DATABASE_URL, **opcoes_do_engine(DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
