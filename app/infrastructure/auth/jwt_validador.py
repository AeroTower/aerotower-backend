import logging

import jwt

from app.application.ports.autenticacao import ValidadorDeSessao
from app.domain.exceptions import NaoAutenticado

logger = logging.getLogger(__name__)

EMISSOR = "aerotower-auth"   # o servico de autenticacao
AUDIENCIA = "aerotower"


class JwtValidador(ValidadorDeSessao):
    def __init__(self, segredo: str):
        if not segredo:
            logger.warning("JWT_SEGREDO vazio: nenhum login será aceito.")
        self._segredo = segredo

    def validar(self, token: str) -> str:
        if not self._segredo:
            raise NaoAutenticado("Servidor sem JWT_SEGREDO configurado.")
        try:
            dados = jwt.decode(
                token, self._segredo, algorithms=["HS256"],
                issuer=EMISSOR, audience=AUDIENCIA,
                options={"require": ["sub", "exp", "iss", "aud"]},
            )
        except jwt.ExpiredSignatureError:
            raise NaoAutenticado("Sessão expirada. Faça login de novo.")
        except jwt.PyJWTError:
            raise NaoAutenticado("Sessão inválida. Faça login de novo.")
        return dados["sub"]
