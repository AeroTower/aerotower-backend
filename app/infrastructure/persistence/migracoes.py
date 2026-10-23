"""Ajustes de esquema que o create_all nao faz.

O Base.metadata.create_all so cria tabelas que nao existem; coluna nova em
tabela antiga precisa ser adicionada a mao. Cada ajuste aqui confere se ja
foi feito antes de agir, entao rodar a cada start e seguro.
"""
import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def aplicar(engine: Engine) -> None:
    _coluna_torre_em_plantas(engine)


def _coluna_torre_em_plantas(engine: Engine) -> None:
    inspetor = inspect(engine)
    if "plantas" not in inspetor.get_table_names():
        return
    colunas = {c["name"] for c in inspetor.get_columns("plantas")}
    if "torre_id" in colunas:
        return
    with engine.begin() as conexao:
        conexao.execute(text("ALTER TABLE plantas ADD COLUMN torre_id VARCHAR"))
        conexao.execute(text("CREATE INDEX IF NOT EXISTS ix_plantas_torre_id ON plantas (torre_id)"))
    logger.info("Migração: coluna plantas.torre_id criada (plantas antigas ficam sem torre).")
