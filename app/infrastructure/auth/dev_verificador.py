import re

from app.application.ports.autenticacao import VerificadorDeIdentidade
from app.domain.entities.usuario import Usuario
from app.domain.exceptions import NaoAutenticado

_ID_VALIDO = re.compile(r"^[A-Za-z0-9._@+-]{1,64}$")


class DevVerificador(VerificadorDeIdentidade):
    """'Login' sem Google, so com AUTH_MODO_DEV=true.

    Qualquer texto vira um usuario "dev:<texto>". Serve para o app andar
    enquanto o login real nao fica pronto, e para os testes. O prefixo
    garante que um usuario de teste nunca se confunda com uma conta Google.
    """

    def __init__(self, habilitado: bool):
        self._habilitado = habilitado

    def verificar(self, token: str) -> Usuario:
        if not self._habilitado:
            raise NaoAutenticado("Login de desenvolvimento desligado neste servidor.")
        identificador = (token or "").strip()
        if not _ID_VALIDO.match(identificador):
            raise NaoAutenticado("Identificador de desenvolvimento inválido.")
        return Usuario(id=f"dev:{identificador}", email=None, nome=identificador)
