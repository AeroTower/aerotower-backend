from typing import List

from app.domain.entities.torre import Torre
from app.domain.exceptions import TorreNaoEncontrada
from app.domain.repositories.torre_repository import TorreRepository


class ListarMinhasTorres:
    def __init__(self, torres: TorreRepository):
        self._torres = torres

    def executar(self, usuario_id: str) -> List[Torre]:
        return self._torres.listar_do_dono(usuario_id)


class ObterTorreDoUsuario:
    """A checagem de acesso de toda rota /torres/{id}/...

    Torre de outra pessoa e torre inexistente dao o mesmo 404.
    """

    def __init__(self, torres: TorreRepository):
        self._torres = torres

    def executar(self, usuario_id: str, torre_id: str) -> Torre:
        torre = self._torres.buscar(torre_id)
        if torre is None or not torre.pertence_a(usuario_id):
            raise TorreNaoEncontrada(torre_id)
        return torre
