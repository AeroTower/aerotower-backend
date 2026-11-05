import logging
from app.application.ports.armazenamento_fotos import ArmazenamentoDeFotos
from app.domain.exceptions import PlantaNaoEncontrada
from app.domain.repositories.planta_repository import PlantaRepository

logger = logging.getLogger(__name__)


class DeletarPlanta:
    def __init__(self, repositorio: PlantaRepository, armazenamento: ArmazenamentoDeFotos):
        self._repositorio = repositorio
        self._armazenamento = armazenamento

    def executar(self, planta_id: int, torre_id: str, usuario_id: str) -> str:
        # Planta de outra torre ou de outra pessoa = nao encontrada.
        planta = self._repositorio.buscar_por_id(planta_id, torre_id, usuario_id)
        if planta is None:
            raise PlantaNaoEncontrada(planta_id)

        nome = planta.nome
        self._armazenamento.remover(planta.foto_url)
        self._repositorio.remover(planta_id)
        logger.info("Planta removida: %s", nome)
        return nome
