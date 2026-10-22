from abc import ABC, abstractmethod
from typing import List, Optional


class CatalogoDeTorres(ABC):
    """Consulta rapida usada no caminho do MQTT (muitas mensagens por segundo)."""

    @abstractmethod
    def capacidades(self, torre_id: str) -> Optional[List[str]]:
        """Capacidades do kit cadastrado, ou None se a torre nao foi cadastrada."""
