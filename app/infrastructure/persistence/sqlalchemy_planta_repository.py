from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.entities.planta import Planta
from app.domain.repositories.planta_repository import PlantaRepository
from app.infrastructure.persistence.models import PlantaModel


class SqlAlchemyPlantaRepository(PlantaRepository):
    def __init__(self, session: Session):
        self._session = session

    def _da_torre(self, torre_id: Optional[str]):
        consulta = self._session.query(PlantaModel)
        if torre_id is None:
            return consulta.filter(PlantaModel.torre_id.is_(None))
        return consulta.filter(PlantaModel.torre_id == torre_id)

    def listar(self, torre_id: Optional[str]) -> List[Planta]:
        modelos = self._da_torre(torre_id).order_by(PlantaModel.id).all()
        return [self._para_entidade(m) for m in modelos]

    def buscar_por_id(self, planta_id: int, torre_id: Optional[str]) -> Optional[Planta]:
        modelo = self._da_torre(torre_id).filter(PlantaModel.id == planta_id).first()
        return self._para_entidade(modelo) if modelo is not None else None

    def criar(self, planta: Planta) -> Planta:
        modelo = PlantaModel(
            nome         = planta.nome,
            tipo         = planta.tipo,
            data_plantio = planta.data_plantio,
            foto_url     = planta.foto_url,
            torre_id     = planta.torre_id,
        )
        self._session.add(modelo)
        self._session.commit()
        self._session.refresh(modelo)
        return self._para_entidade(modelo)

    def remover(self, planta_id: int) -> None:
        modelo = self._session.get(PlantaModel, planta_id)
        if modelo is not None:
            self._session.delete(modelo)
            self._session.commit()

    @staticmethod
    def _para_entidade(modelo: PlantaModel) -> Planta:
        return Planta(
            id           = modelo.id,
            nome         = modelo.nome,
            tipo         = modelo.tipo,
            data_plantio = modelo.data_plantio,
            foto_url     = modelo.foto_url,
            torre_id     = modelo.torre_id,
        )
