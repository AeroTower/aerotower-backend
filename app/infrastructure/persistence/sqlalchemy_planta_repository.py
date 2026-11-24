from typing import List, Optional

from app.domain.entities.planta import Planta
from app.domain.repositories.planta_repository import PlantaRepository
from app.infrastructure.persistence.models import PlantaModel
from app.infrastructure.persistence.repositorio_base import RepositorioSqlAlchemy


class SqlAlchemyPlantaRepository(RepositorioSqlAlchemy, PlantaRepository):
    def _de(self, torre_id: str, usuario_id: str):
        """Consulta ja filtrada pelo dono: toda leitura passa por aqui."""
        return self._session.query(PlantaModel).filter(
            PlantaModel.torre_id == torre_id,
            PlantaModel.usuario_id == usuario_id,
        )

    def listar(self, torre_id: str, usuario_id: str) -> List[Planta]:
        modelos = self._de(torre_id, usuario_id).order_by(PlantaModel.id).all()
        return [self._para_entidade(m) for m in modelos]

    def buscar_por_id(self, planta_id: int, torre_id: str, usuario_id: str) -> Optional[Planta]:
        modelo = self._de(torre_id, usuario_id).filter(PlantaModel.id == planta_id).first()
        return self._para_entidade(modelo) if modelo is not None else None

    def criar(self, planta: Planta) -> Planta:
        modelo = self._salvar(PlantaModel(
            nome         = planta.nome,
            tipo         = planta.tipo,
            data_plantio = planta.data_plantio,
            foto_url     = planta.foto_url,
            torre_id     = planta.torre_id,
            usuario_id   = planta.usuario_id,
        ))
        return self._para_entidade(modelo)

    def remover(self, planta_id: int) -> None:
        # Nao filtra por dono de proposito: o caso de uso DeletarPlanta ja
        # confere com buscar_por_id(id, torre, usuario) antes de chamar aqui.
        modelo = self._session.get(PlantaModel, planta_id)
        if modelo is not None:
            self._session.delete(modelo)
            self._commit()

    @staticmethod
    def _para_entidade(modelo: PlantaModel) -> Planta:
        return Planta(
            id           = modelo.id,
            nome         = modelo.nome,
            tipo         = modelo.tipo,
            data_plantio = modelo.data_plantio,
            foto_url     = modelo.foto_url,
            torre_id     = modelo.torre_id,
            usuario_id   = modelo.usuario_id,
        )
