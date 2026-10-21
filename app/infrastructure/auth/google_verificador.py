import logging
from typing import Iterable

from app.application.ports.autenticacao import VerificadorDeIdentidade
from app.domain.entities.usuario import Usuario
from app.domain.exceptions import NaoAutenticado

logger = logging.getLogger(__name__)

_EMISSORES = {"accounts.google.com", "https://accounts.google.com"}


class GoogleVerificador(VerificadorDeIdentidade):
    """Valida o ID token que o pacote google_sign_in entrega ao app.

    Confere assinatura (chaves publicas do Google), validade, emissor e se o
    token foi emitido para um dos NOSSOS client IDs — sem essa ultima
    checagem, um token de qualquer outro app com login Google passaria.
    """

    def __init__(self, client_ids: Iterable[str]):
        self._client_ids = set(client_ids)

    def verificar(self, token: str) -> Usuario:
        if not self._client_ids:
            raise NaoAutenticado(
                "Login com Google não configurado no servidor (GOOGLE_CLIENT_IDS vazio)."
            )
        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token

            dados = id_token.verify_oauth2_token(token, google_requests.Request())
        except Exception as erro:
            logger.info("Token Google recusado: %s", erro)
            raise NaoAutenticado("Token do Google inválido ou expirado.")

        if dados.get("iss") not in _EMISSORES:
            raise NaoAutenticado("Token não foi emitido pelo Google.")
        if dados.get("aud") not in self._client_ids:
            raise NaoAutenticado("Token do Google emitido para outro aplicativo.")
        if dados.get("email") and dados.get("email_verified") is False:
            raise NaoAutenticado("E-mail da conta Google não verificado.")

        return Usuario(id=dados["sub"], email=dados.get("email"), nome=dados.get("name"))
