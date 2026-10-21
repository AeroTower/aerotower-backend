import logging
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.application.ports.autenticacao import EmissorDeSessao
from app.domain.entities.usuario import Usuario
from app.domain.exceptions import NaoAutenticado

logger = logging.getLogger(__name__)


class JwtEmissor(EmissorDeSessao):
    _ALGORITMO = "HS256"
    _EMISSOR = "aerotower-backend"

    def __init__(self, segredo: str, validade_dias: int = 30):
        if not segredo:
            logger.warning(
                "JWT_SEGREDO não definido: usando um segredo aleatório. "
                "Todo restart do servidor desloga todo mundo."
            )
            segredo = secrets.token_urlsafe(48)
        self._segredo = segredo
        self._validade = timedelta(days=validade_dias)

    def emitir(self, usuario: Usuario) -> str:
        agora = datetime.now(timezone.utc)
        return jwt.encode(
            {"sub": usuario.id, "iss": self._EMISSOR, "iat": agora, "exp": agora + self._validade},
            self._segredo,
            algorithm=self._ALGORITMO,
        )

    def validar(self, token: str) -> str:
        try:
            dados = jwt.decode(
                token,
                self._segredo,
                algorithms=[self._ALGORITMO],
                issuer=self._EMISSOR,
                options={"require": ["sub", "exp", "iss"]},
            )
        except jwt.ExpiredSignatureError:
            raise NaoAutenticado("Sessão expirada. Faça login de novo.")
        except jwt.PyJWTError:
            raise NaoAutenticado("Sessão inválida. Faça login de novo.")
        return dados["sub"]
