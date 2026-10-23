import logging
from typing import Optional

from app.application.ports.armazenamento_fotos import ArmazenamentoDeFotos
from app.domain.entities.planta import Planta
from app.domain.exceptions import FormatoDeFotoInvalido
from app.domain.repositories.planta_repository import PlantaRepository

logger = logging.getLogger(__name__)


class CriarPlanta:
    def __init__(self, repositorio: PlantaRepository, armazenamento: ArmazenamentoDeFotos):
        self._repositorio = repositorio
        self._armazenamento = armazenamento

    async def executar(
        self,
        nome: str,
        tipo: str,
        data_plantio: str,
        nome_arquivo_foto: Optional[str] = None,
        conteudo_foto: Optional[bytes] = None,
        torre_id: Optional[str] = None,
    ) -> Planta:
        foto_url = None
        if nome_arquivo_foto and conteudo_foto is not None:
            extensao = nome_arquivo_foto.split(".")[-1].lower()
            aceitas = self._armazenamento.extensoes_aceitas()
            if extensao not in aceitas:
                raise FormatoDeFotoInvalido(aceitas)
            foto_url = await self._armazenamento.salvar(conteudo_foto, extensao)

        planta = self._repositorio.criar(
            Planta(nome=nome, tipo=tipo, data_plantio=data_plantio, foto_url=foto_url,
                   torre_id=torre_id)
        )
        logger.info("Planta cadastrada: %s (%s) na torre %s", planta.nome, planta.tipo, torre_id)
        return planta
