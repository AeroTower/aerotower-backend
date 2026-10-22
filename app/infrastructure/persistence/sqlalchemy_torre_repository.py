from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.entities.kit import Kit
from app.domain.entities.torre import Torre
from app.domain.repositories.torre_repository import TorreRepository
from app.infrastructure.persistence.models import TorreModel


class SqlAlchemyTorreRepository(TorreRepository):
    def __init__(self, session: Session):
        self._session = session

    def buscar(self, torre_id: str) -> Optional[Torre]:
        modelo = self._session.get(TorreModel, torre_id)
        return self._para_entidade(modelo) if modelo else None

    def listar_do_dono(self, dono_id: str) -> List[Torre]:
        modelos = (
            self._session.query(TorreModel)
            .filter(TorreModel.dono_id == dono_id)
            .order_by(TorreModel.ativada_em)
            .all()
        )
        return [self._para_entidade(m) for m in modelos]

    def aplicar_estado(self, torre: Torre, versao: int) -> bool:
        modelo = self._session.get(TorreModel, torre.id)
        if modelo is not None and modelo.versao >= versao:
            return False
        if modelo is None:
            modelo = TorreModel(id=torre.id, criada_em=datetime.now())
            self._session.add(modelo)
        if torre.dono_id != modelo.dono_id:
            modelo.ativada_em = datetime.now() if torre.dono_id else None
        modelo.kit     = torre.kit.value
        modelo.dono_id = torre.dono_id
        modelo.apelido = torre.apelido
        modelo.versao  = versao
        self._session.commit()
        return True

    @staticmethod
    def _para_entidade(modelo: TorreModel) -> Torre:
        return Torre(
            id         = modelo.id,
            kit        = Kit(modelo.kit),
            dono_id    = modelo.dono_id,
            apelido    = modelo.apelido,
            criada_em  = modelo.criada_em,
            ativada_em = modelo.ativada_em,
        )
