from typing import List, Optional

from app.domain.entities.planta import Planta
from app.domain.repositories.planta_repository import PlantaRepository


class ListarPlantas:
    def __init__(self, repositorio: PlantaRepository):
        self._repositorio = repositorio

    def executar(self, torre_id: Optional[str] = None) -> List[Planta]:
        return self._repositorio.listar(torre_id)
