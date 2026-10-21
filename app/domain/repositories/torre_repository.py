from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.torre import Torre


class TorreRepository(ABC):
    @abstractmethod
    def buscar(self, torre_id: str) -> Optional[Torre]:
        ...

    @abstractmethod
    def buscar_por_codigo(self, codigo_hash: str) -> Optional[Torre]:
        """Torre ainda nao ativada cujo codigo tem este hash."""

    @abstractmethod
    def listar_do_dono(self, dono_id: str) -> List[Torre]:
        ...

    @abstractmethod
    def listar_todas(self) -> List[Torre]:
        ...

    @abstractmethod
    def criar(self, torre: Torre, codigo_hash: str) -> Torre:
        ...

    @abstractmethod
    def vincular_dono(self, torre_id: str, dono_id: str, apelido: Optional[str]) -> Torre:
        """Grava o dono e queima o codigo (ele vale uma vez so)."""

    @abstractmethod
    def trocar_codigo(self, torre_id: str, codigo_hash: str) -> None:
        """Tira o dono e grava um codigo novo (revenda, troca de conta)."""
