from typing import Tuple

from app.application.ports.autenticacao import EmissorDeSessao, VerificadorDeIdentidade
from app.domain.entities.usuario import Usuario
from app.domain.repositories.usuario_repository import UsuarioRepository


class Autenticar:
    """Troca um token do provedor (Google, ou o de desenvolvimento) por uma sessao nossa."""

    def __init__(
        self,
        verificador: VerificadorDeIdentidade,
        usuarios: UsuarioRepository,
        emissor: EmissorDeSessao,
    ):
        self._verificador = verificador
        self._usuarios = usuarios
        self._emissor = emissor

    def executar(self, token_do_provedor: str) -> Tuple[str, Usuario]:
        usuario = self._verificador.verificar(token_do_provedor)
        usuario = self._usuarios.salvar(usuario)
        return self._emissor.emitir(usuario), usuario
