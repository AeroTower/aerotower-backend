import threading
from collections import defaultdict
from typing import Dict, Optional

from app.application.ports.estado_monitoramento import EstadoDeMonitoramento
from app.domain.entities.leitura import LeituraAvaliada, StatusMotor
from app.domain.entities.presenca import Presenca
from app.domain.entities.thresholds import Thresholds


class EstadoEmMemoria(EstadoDeMonitoramento):
    """Ultimo estado de cada torre, num dicionario por id.

    Continua em memoria (some num restart), como antes. Thresholds por torre
    sao o primeiro candidato a ir para o banco.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._leituras: Dict[str, LeituraAvaliada] = {}
        self._status_motor: Dict[str, StatusMotor] = {}
        self._thresholds: Dict[str, Thresholds] = defaultdict(Thresholds)
        self._presencas: Dict[str, Presenca] = defaultdict(Presenca)

    def salvar_leitura(self, torre_id: str, leitura: LeituraAvaliada) -> None:
        with self._lock:
            self._leituras[torre_id] = leitura

    def ultima_leitura(self, torre_id: str) -> Optional[LeituraAvaliada]:
        with self._lock:
            return self._leituras.get(torre_id)

    def salvar_status_motor(self, torre_id: str, status: StatusMotor) -> None:
        with self._lock:
            self._status_motor[torre_id] = status

    def ultimo_status_motor(self, torre_id: str) -> Optional[StatusMotor]:
        with self._lock:
            return self._status_motor.get(torre_id)

    def thresholds(self, torre_id: str) -> Thresholds:
        with self._lock:
            return self._thresholds[torre_id]

    def presenca(self, torre_id: str) -> Presenca:
        with self._lock:
            return self._presencas[torre_id]
