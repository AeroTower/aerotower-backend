from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.planta import Planta


class PlantaRepository(ABC):
    """Plantas sempre filtradas por torre E por usuario (o dono atual)."""

    @abstractmethod
    def listar(self, torre_id: str, usuario_id: str) -> List[Planta]:
        ...

    @abstractmethod
    def buscar_por_id(self, planta_id: int, torre_id: str, usuario_id: str) -> Optional[Planta]:
        ...

    @abstractmethod
    def criar(self, planta: Planta) -> Planta:
        ...

    @abstractmethod
    def remover(self, planta_id: int) -> None:
        ...
