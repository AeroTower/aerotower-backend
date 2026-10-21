from abc import ABC, abstractmethod

from app.domain.entities.leitura import ComandoMotor


class PublicadorDeComandos(ABC):
    @abstractmethod
    def publicar(self, torre_id: str, comando: ComandoMotor) -> None:
        ...
