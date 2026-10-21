from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.usuario import Usuario


class UsuarioRepository(ABC):
    @abstractmethod
    def salvar(self, usuario: Usuario) -> Usuario:
        """Cria ou atualiza (e-mail e nome podem mudar; o id nao)."""

    @abstractmethod
    def buscar(self, usuario_id: str) -> Optional[Usuario]:
        ...
