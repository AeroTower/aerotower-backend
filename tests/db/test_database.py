"""Testes da configuracao do engine (app/infrastructure/persistence/database.py)."""
from app.infrastructure.persistence.database import opcoes_do_engine


def test_sqlite_desliga_check_same_thread():
    assert opcoes_do_engine("sqlite:///./plantas.db") == {"connect_args": {"check_same_thread": False}}


def test_postgres_testa_conexao_antes_de_usar():
    """Azure fecha conexoes ociosas; pool_pre_ping evita erro 500 depois."""
    opcoes = opcoes_do_engine("postgresql://u:s@servidor:5432/aerotower")
    assert opcoes["pool_pre_ping"] is True
    assert opcoes["pool_recycle"] == 1800
    assert "connect_args" not in opcoes   # check_same_thread derruba o Postgres
