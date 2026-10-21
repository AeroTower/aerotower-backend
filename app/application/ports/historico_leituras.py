from abc import ABC, abstractmethod
from typing import Any, Dict


class HistoricoDeLeituras(ABC):
    @abstractmethod
    def registrar(self, torre_id: str, dados: Dict[str, Any]) -> None:
        ...
