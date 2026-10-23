from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.planta import Planta


class PlantaRepository(ABC):
    """Plantas sempre filtradas por torre: torre_id None = plantas legadas."""

    @abstractmethod
    def listar(self, torre_id: Optional[str]) -> List[Planta]:
        ...

    @abstractmethod
    def buscar_por_id(self, planta_id: int, torre_id: Optional[str]) -> Optional[Planta]:
        ...

    @abstractmethod
    def criar(self, planta: Planta) -> Planta:
        ...

    @abstractmethod
    def remover(self, planta_id: int) -> None:
        ...
