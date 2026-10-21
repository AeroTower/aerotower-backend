import logging
from datetime import datetime
from typing import List, Tuple

from app.domain.entities.kit import Kit
from app.domain.entities.torre import Torre, id_de_torre_valido
from app.domain.exceptions import IdDeTorreInvalido, TorreJaCadastrada, TorreNaoEncontrada
from app.domain.repositories.torre_repository import TorreRepository
from app.domain.services.codigo_ativacao import gerar_codigo, hash_codigo

logger = logging.getLogger(__name__)


class CadastrarTorre:
    """Etapa de fabrica: registra a placa e devolve o codigo do adesivo.

    O codigo em texto puro so existe nesta resposta. O banco guarda o hash;
    se o adesivo se perder, use GerarNovoCodigo.
    """

    def __init__(self, torres: TorreRepository):
        self._torres = torres

    def executar(self, torre_id: str, kit: Kit) -> Tuple[Torre, str]:
        torre_id = (torre_id or "").strip().upper()
        if not id_de_torre_valido(torre_id):
            raise IdDeTorreInvalido(torre_id)
        if self._torres.buscar(torre_id) is not None:
            raise TorreJaCadastrada(torre_id)

        codigo = gerar_codigo()
        torre = self._torres.criar(
            Torre(id=torre_id, kit=kit, criada_em=datetime.now()),
            hash_codigo(codigo),
        )
        logger.info("Torre %s cadastrada (kit %s)", torre_id, kit.value)
        return torre, codigo


class GerarNovoCodigo:
    """Adesivo perdido, revenda ou troca de conta: desvincula e gera outro codigo."""

    def __init__(self, torres: TorreRepository):
        self._torres = torres

    def executar(self, torre_id: str) -> Tuple[Torre, str]:
        torre = self._torres.buscar(torre_id)
        if torre is None:
            raise TorreNaoEncontrada(torre_id)
        codigo = gerar_codigo()
        self._torres.trocar_codigo(torre_id, hash_codigo(codigo))
        logger.info("Novo código gerado para a torre %s", torre_id)
        return self._torres.buscar(torre_id), codigo


class ListarTodasAsTorres:
    def __init__(self, torres: TorreRepository):
        self._torres = torres

    def executar(self) -> List[Torre]:
        return self._torres.listar_todas()
