from abc import ABC, abstractmethod


class ValidadorDeSessao(ABC):
    """Confere o token emitido pelo servico de autenticacao (auth-aerotower).

    O Backend nao faz login: so verifica a assinatura com o segredo
    compartilhado (JWT_SEGREDO) e le quem e a pessoa.
    """

    @abstractmethod
    def validar(self, token: str) -> str:
        """Devolve o id do usuario ou levanta NaoAutenticado."""
