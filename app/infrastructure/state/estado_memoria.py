import threading
from typing import Optional

from app.application.ports.estado_monitoramento import EstadoDeMonitoramento
from app.domain.entities.leitura import LeituraAvaliada, StatusMotor
from app.domain.entities.thresholds import Thresholds


class EstadoEmMemoria(EstadoDeMonitoramento):
    def __init__(self):
        self._lock = threading.Lock()
        self._ultima_leitura: Optional[LeituraAvaliada] = None
        self._ultimo_status_motor: Optional[StatusMotor] = None
        self._thresholds = Thresholds()

    def salvar_leitura(self, leitura: LeituraAvaliada) -> None:
        with self._lock:
            self._ultima_leitura = leitura

    def ultima_leitura(self) -> Optional[LeituraAvaliada]:
        with self._lock:
            return self._ultima_leitura

    def salvar_status_motor(self, status: StatusMotor) -> None:
        with self._lock:
            self._ultimo_status_motor = status

    def ultimo_status_motor(self) -> Optional[StatusMotor]:
        with self._lock:
            return self._ultimo_status_motor

    def thresholds(self) -> Thresholds:
        return self._thresholds
    
    def salvar_thresholds(self, thresholds: Thresholds) -> None:
        pass  # em memória o objeto já foi alterado, não há o que salvar
