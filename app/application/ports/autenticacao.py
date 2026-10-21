from abc import ABC, abstractmethod

from app.domain.entities.usuario import Usuario


class VerificadorDeIdentidade(ABC):
    """Confere um token de um provedor externo (Google) e diz quem e a pessoa."""

    @abstractmethod
    def verificar(self, token: str) -> Usuario:
        """Levanta NaoAutenticado se o token nao for valido."""


class EmissorDeSessao(ABC):
    """Token proprio do back-end, emitido depois do login.

    O ID token do Google expira em 1 h; trocar por um token nosso, de vida
    mais longa, poupa o app de renovar o login do Google a toda hora e
    deixa o resto da API independente de qual provedor fez o login.
    """

    @abstractmethod
    def emitir(self, usuario: Usuario) -> str:
        ...

    @abstractmethod
    def validar(self, token: str) -> str:
        """Devolve o id do usuario ou levanta NaoAutenticado."""
