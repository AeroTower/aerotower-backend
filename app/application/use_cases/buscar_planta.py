from typing import Optional

from app.domain.entities.planta import Planta
from app.domain.exceptions import PlantaNaoEncontrada
from app.domain.repositories.planta_repository import PlantaRepository


class BuscarPlanta:
    def __init__(self, repositorio: PlantaRepository):
        self._repositorio = repositorio

    def executar(self, planta_id: int, torre_id: Optional[str] = None) -> Planta:
        planta = self._repositorio.buscar_por_id(planta_id, torre_id)
        if planta is None:
            raise PlantaNaoEncontrada(planta_id)
        return planta
