from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.leitura import LeituraAvaliada, StatusMotor
from app.domain.entities.presenca import Presenca
from app.domain.entities.thresholds import Thresholds


class EstadoDeMonitoramento(ABC):
    """Ultimo estado conhecido de CADA torre, separado pelo id."""

    @abstractmethod
    def salvar_leitura(self, torre_id: str, leitura: LeituraAvaliada) -> None:
        ...

    @abstractmethod
    def ultima_leitura(self, torre_id: str) -> Optional[LeituraAvaliada]:
        ...

    @abstractmethod
    def salvar_status_motor(self, torre_id: str, status: StatusMotor) -> None:
        ...

    @abstractmethod
    def ultimo_status_motor(self, torre_id: str) -> Optional[StatusMotor]:
        ...

    @abstractmethod
    def thresholds(self, torre_id: str) -> Thresholds:
        ...

    @abstractmethod
    def presenca(self, torre_id: str) -> Presenca:
        ...
