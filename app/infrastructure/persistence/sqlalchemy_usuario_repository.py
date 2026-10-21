from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.domain.entities.usuario import Usuario
from app.domain.repositories.usuario_repository import UsuarioRepository
from app.infrastructure.persistence.models import UsuarioModel


class SqlAlchemyUsuarioRepository(UsuarioRepository):
    def __init__(self, session: Session):
        self._session = session

    def salvar(self, usuario: Usuario) -> Usuario:
        modelo = self._session.get(UsuarioModel, usuario.id)
        if modelo is None:
            modelo = UsuarioModel(id=usuario.id, criado_em=datetime.now())
            self._session.add(modelo)
        modelo.email = usuario.email
        modelo.nome  = usuario.nome
        self._session.commit()
        return Usuario(id=modelo.id, email=modelo.email, nome=modelo.nome)

    def buscar(self, usuario_id: str) -> Optional[Usuario]:
        modelo = self._session.get(UsuarioModel, usuario_id)
        if modelo is None:
            return None
        return Usuario(id=modelo.id, email=modelo.email, nome=modelo.nome)
