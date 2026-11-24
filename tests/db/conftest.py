"""Fixtures compartilhadas pelos testes de banco de dados.

Como funciona:
- Por padrao, os testes SQL rodam num SQLite em memoria (nao precisa de nada
  instalado). Se a variavel TEST_DATABASE_URL estiver definida (ex.: um
  Postgres local), os MESMOS testes rodam tambem contra ele.
- Os testes de Redis usam um Redis real se TEST_REDIS_URL estiver definida;
  senao usam o fakeredis (um Redis falso em memoria, mesmo comportamento).

Nunca aponte TEST_DATABASE_URL para o banco de producao: as tabelas sao
apagadas e recriadas a cada teste.
"""
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Garante que "import app..." funcione rodando o pytest da raiz do repo.
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from app.infrastructure.persistence.database import Base  # noqa: E402
from app.infrastructure.persistence import models  # noqa: E402,F401  (registra as tabelas no Base)


def _urls_de_banco():
    urls = ["sqlite://"]  # "sqlite://" = SQLite em memoria
    extra = os.getenv("TEST_DATABASE_URL")
    if extra:
        urls.append(extra)
    return urls


@pytest.fixture(params=_urls_de_banco(), ids=lambda u: u.split(":")[0])
def engine(request):
    """Um engine novo por teste, com as tabelas criadas do zero."""
    url = request.param
    kwargs = {}
    if url.startswith("sqlite"):
        # StaticPool: todas as conexoes enxergam o MESMO banco em memoria.
        from sqlalchemy.pool import StaticPool
        kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
    eng = create_engine(url, **kwargs)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session(engine):
    """Sessao do SQLAlchemy ligada ao engine do teste."""
    Sessao = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    s = Sessao()
    yield s
    s.rollback()
    s.close()


@pytest.fixture
def nova_sessao(engine):
    """Abre uma sessao NOVA, para conferir que o dado foi mesmo gravado
    no banco (e nao so ficou no cache da sessao que gravou)."""
    Sessao = sessionmaker(bind=engine)
    abertas = []

    def _abrir():
        s = Sessao()
        abertas.append(s)
        return s

    yield _abrir
    for s in abertas:
        s.close()


@pytest.fixture
def redis_url():
    return os.getenv("TEST_REDIS_URL")
