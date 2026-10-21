from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.entities.kit import Kit
from app.domain.entities.torre import Torre
from app.domain.exceptions import CodigoDeAtivacaoInvalido
from app.domain.repositories.torre_repository import TorreRepository
from app.infrastructure.persistence.models import TorreModel


class SqlAlchemyTorreRepository(TorreRepository):
    def __init__(self, session: Session):
        self._session = session

    def buscar(self, torre_id: str) -> Optional[Torre]:
        modelo = self._session.get(TorreModel, torre_id)
        return self._para_entidade(modelo) if modelo else None

    def buscar_por_codigo(self, codigo_hash: str) -> Optional[Torre]:
        modelo = (
            self._session.query(TorreModel)
            .filter(TorreModel.codigo_hash == codigo_hash, TorreModel.dono_id.is_(None))
            .first()
        )
        return self._para_entidade(modelo) if modelo else None

    def listar_do_dono(self, dono_id: str) -> List[Torre]:
        modelos = (
            self._session.query(TorreModel)
            .filter(TorreModel.dono_id == dono_id)
            .order_by(TorreModel.ativada_em)
            .all()
        )
        return [self._para_entidade(m) for m in modelos]

    def listar_todas(self) -> List[Torre]:
        modelos = self._session.query(TorreModel).order_by(TorreModel.criada_em).all()
        return [self._para_entidade(m) for m in modelos]

    def criar(self, torre: Torre, codigo_hash: str) -> Torre:
        modelo = TorreModel(
            id          = torre.id,
            kit         = torre.kit.value,
            codigo_hash = codigo_hash,
            criada_em   = torre.criada_em or datetime.now(),
        )
        self._session.add(modelo)
        self._session.commit()
        return self._para_entidade(modelo)

    def vincular_dono(self, torre_id: str, dono_id: str, apelido: Optional[str]) -> Torre:
        # UPDATE condicional: se dois celulares usarem o mesmo codigo ao
        # mesmo tempo, so um encontra dono_id ainda NULL.
        alteradas = (
            self._session.query(TorreModel)
            .filter(TorreModel.id == torre_id, TorreModel.dono_id.is_(None))
            .update({
                TorreModel.dono_id:     dono_id,
                TorreModel.apelido:     apelido,
                TorreModel.codigo_hash: None,
                TorreModel.ativada_em:  datetime.now(),
            }, synchronize_session=False)
        )
        self._session.commit()
        if alteradas == 0:
            raise CodigoDeAtivacaoInvalido()
        return self.buscar(torre_id)

    def trocar_codigo(self, torre_id: str, codigo_hash: str) -> None:
        modelo = self._session.get(TorreModel, torre_id)
        if modelo is None:
            return
        modelo.codigo_hash = codigo_hash
        modelo.dono_id     = None
        modelo.apelido     = None
        modelo.ativada_em  = None
        self._session.commit()

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
