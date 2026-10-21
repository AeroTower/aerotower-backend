import logging
from typing import Optional

from app.domain.entities.torre import Torre
from app.domain.exceptions import CodigoDeAtivacaoInvalido
from app.domain.repositories.torre_repository import TorreRepository
from app.domain.services.codigo_ativacao import formato_valido, hash_codigo

logger = logging.getLogger(__name__)


class AtivarTorre:
    """Liga a pessoa logada a torre do adesivo. O codigo vale uma vez so."""

    def __init__(self, torres: TorreRepository):
        self._torres = torres

    def executar(self, usuario_id: str, codigo: str, apelido: Optional[str] = None) -> Torre:
        if not formato_valido(codigo):
            raise CodigoDeAtivacaoInvalido()

        torre = self._torres.buscar_por_codigo(hash_codigo(codigo))
        if torre is None:
            # Mesmo erro para "nao existe" e "ja usado": nao ajuda quem
            # estiver chutando codigos.
            raise CodigoDeAtivacaoInvalido()

        torre = self._torres.vincular_dono(torre.id, usuario_id, apelido)
        logger.info("Torre %s ativada pelo usuário %s", torre.id, usuario_id)
        return torre
