import logging
from typing import Optional

from app.domain.entities.kit import Kit
from app.domain.entities.torre import Torre, id_de_torre_valido
from app.domain.exceptions import IdDeTorreInvalido
from app.domain.repositories.torre_repository import TorreRepository

logger = logging.getLogger(__name__)


class SincronizarTorre:
    """Aplica o estado de uma torre vindo de um evento do servico de auth."""

    def __init__(self, torres: TorreRepository):
        self._torres = torres

    def executar(self, torre_id: str, kit: Kit, dono_id: Optional[str],
                 apelido: Optional[str], versao: int) -> bool:
        torre_id = (torre_id or "").upper()
        if not id_de_torre_valido(torre_id):
            raise IdDeTorreInvalido(torre_id)
        aplicado = self._torres.aplicar_estado(
            Torre(id=torre_id, kit=kit, dono_id=dono_id, apelido=apelido), versao
        )
        logger.info("Torre %s %s (v%s, dono=%s)", torre_id,
                    "sincronizada" if aplicado else "ignorada: evento antigo", versao, dono_id)
        return aplicado
