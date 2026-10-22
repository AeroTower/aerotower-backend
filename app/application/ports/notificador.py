from abc import ABC, abstractmethod
from typing import Any, Dict


class Notificador(ABC):
    @abstractmethod
    def notificar(self, torre_id: str, payload: Dict[str, Any]) -> None:
        """Entrega o payload so a quem esta acompanhando esta torre."""
