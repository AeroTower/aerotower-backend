"""Testes das migracoes manuais (app/infrastructure/persistence/migracoes.py).

Simula um banco ANTIGO (tabela plantas sem torre_id/usuario_id), roda a
migracao e confere o resultado. Tambem confere que rodar de novo nao estraga
nada, porque o main.py chama migracoes.aplicar() a cada start.
"""
from sqlalchemy import inspect, text

from app.infrastructure.persistence import migracoes
from app.infrastructure.persistence.database import Base


def _criar_tabela_plantas_antiga(engine):
    Base.metadata.drop_all(engine)
    with engine.begin() as c:
        c.execute(text(
            "CREATE TABLE plantas ("
            " id INTEGER PRIMARY KEY, nome VARCHAR NOT NULL, tipo VARCHAR NOT NULL,"
            " data_plantio VARCHAR NOT NULL, foto_url VARCHAR)"
        ))
        c.execute(text(
            "INSERT INTO plantas (id, nome, tipo, data_plantio) VALUES"
            " (1, 'Alface teste', 'folhosa', '2026-05-01'),"
            " (2, 'Rucula teste', 'folhosa', '2026-05-02')"
        ))


def _colunas(engine):
    return {c["name"] for c in inspect(engine).get_columns("plantas")}


def test_migracao_adiciona_colunas_e_apaga_plantas_de_teste(engine):
    _criar_tabela_plantas_antiga(engine)

    migracoes.aplicar(engine)

    assert {"torre_id", "usuario_id"} <= _colunas(engine)
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM plantas")).scalar() == 0


def test_migracao_cria_indices(engine):
    _criar_tabela_plantas_antiga(engine)

    migracoes.aplicar(engine)

    indices = {i["name"] for i in inspect(engine).get_indexes("plantas")}
    assert {"ix_plantas_torre_id", "ix_plantas_usuario_id"} <= indices


def test_migracao_e_idempotente_e_nao_apaga_plantas_novas(engine):
    """Rodar de novo (proximo start do servidor) nao pode apagar dados reais."""
    _criar_tabela_plantas_antiga(engine)
    migracoes.aplicar(engine)
    with engine.begin() as c:
        c.execute(text(
            # id explicito: a tabela "antiga" simulada usa INTEGER PRIMARY KEY,
            # que so gera id sozinho no SQLite (no Postgres precisaria SERIAL).
            "INSERT INTO plantas (id, nome, tipo, data_plantio, torre_id, usuario_id)"
            " VALUES (10, 'Real', 'folhosa', '2026-11-01', 'AT-AAAA1111', 'caio')"
        ))

    migracoes.aplicar(engine)   # segunda vez

    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM plantas")).scalar() == 1


def test_migracao_em_banco_novo_nao_faz_nada(engine):
    """Banco criado pelo create_all ja tem as colunas: nada muda."""
    antes = _colunas(engine)
    migracoes.aplicar(engine)
    assert _colunas(engine) == antes


def test_migracao_sem_tabela_plantas_nao_quebra(engine):
    Base.metadata.drop_all(engine)
    migracoes.aplicar(engine)   # nao deve lancar erro
