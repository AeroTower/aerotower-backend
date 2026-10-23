from typing import Any, Dict

from app.application.ports.estado_monitoramento import EstadoDeMonitoramento
from app.domain.entities.thresholds import Thresholds


class AtualizarThresholds:
    def __init__(self, estado: EstadoDeMonitoramento):
        self._estado = estado

    def executar(self, novos_valores: Dict[str, Any]) -> Thresholds:
        thresholds = self._estado.thresholds()
        thresholds.aplicar(novos_valores)
        self._estado.salvar_thresholds(thresholds)   # novo: persiste
        return thresholds