from datetime import datetime
from typing import List, Optional

from app.domain.entities.kit import Kit
from app.domain.entities.torre import Torre
from app.domain.repositories.torre_repository import TorreRepository
from app.infrastructure.persistence.models import TorreModel
from app.infrastructure.persistence.repositorio_base import RepositorioSqlAlchemy


class SqlAlchemyTorreRepository(RepositorioSqlAlchemy, TorreRepository):
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

    def aplicar_estado(self, torre: Torre, versao: int, forcar: bool = False) -> bool:
        modelo = self._session.get(TorreModel, torre.id)
        if self._evento_velho(modelo, versao) and not forcar:
            return False

        agora = datetime.now()
        if modelo is None:
            modelo = TorreModel(id=torre.id, criada_em=agora)
            self._session.add(modelo)
        if torre.dono_id != modelo.dono_id:
            # Mudou de dono (ou foi desativada): registra quando.
            modelo.ativada_em = agora if torre.dono_id else None

        modelo.kit     = torre.kit.value
        modelo.dono_id = torre.dono_id
        modelo.apelido = torre.apelido
        modelo.versao  = versao
        self._commit()
        return True

    @staticmethod
    def _evento_velho(modelo: Optional[TorreModel], versao: int) -> bool:
        """True se o banco ja tem essa versao ou uma mais nova (evento
        repetido ou que chegou fora de ordem)."""
        return modelo is not None and modelo.versao >= versao

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
