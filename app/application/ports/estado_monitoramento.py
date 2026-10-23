from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.leitura import LeituraAvaliada, StatusMotor
from app.domain.entities.thresholds import Thresholds


class EstadoDeMonitoramento(ABC):
    @abstractmethod
    def salvar_leitura(self, leitura: LeituraAvaliada) -> None:
        ...

    @abstractmethod
    def ultima_leitura(self) -> Optional[LeituraAvaliada]:
        ...

    @abstractmethod
    def salvar_status_motor(self, status: StatusMotor) -> None:
        ...

    @abstractmethod
    def ultimo_status_motor(self) -> Optional[StatusMotor]:
        ...

    @abstractmethod
    def thresholds(self) -> Thresholds:
        ...

    @abstractmethod
    def salvar_thresholds(self, thresholds: Thresholds) -> None:
        ...