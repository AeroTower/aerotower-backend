from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.torre import Torre


class TorreRepository(ABC):
    """Copia local das torres. Quem manda nelas e o servico de autenticacao;
    o Backend recebe o estado pelos eventos (via worker)."""

    @abstractmethod
    def buscar(self, torre_id: str) -> Optional[Torre]:
        ...

    @abstractmethod
    def listar_do_dono(self, dono_id: str) -> List[Torre]:
        ...

    @abstractmethod
    def aplicar_estado(self, torre: Torre, versao: int) -> bool:
        """Grava o estado se `versao` for mais nova que a guardada.

        Devolve False quando o evento e velho (chegou fora de ordem ou
        repetido) e foi ignorado.
        """
