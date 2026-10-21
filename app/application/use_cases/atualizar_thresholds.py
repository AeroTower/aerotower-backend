from typing import Any, Dict

from app.application.ports.estado_monitoramento import EstadoDeMonitoramento
from app.domain.entities.thresholds import Thresholds


class AtualizarThresholds:
    def __init__(self, estado: EstadoDeMonitoramento):
        self._estado = estado

    def executar(self, torre_id: str, novos_valores: Dict[str, Any]) -> Thresholds:
        thresholds = self._estado.thresholds(torre_id)
        thresholds.aplicar(novos_valores)
        return thresholds
