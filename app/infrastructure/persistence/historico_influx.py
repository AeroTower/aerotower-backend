import logging
from typing import Any, Dict

from app.application.ports.historico_leituras import HistoricoDeLeituras

logger = logging.getLogger(__name__)


class HistoricoInflux(HistoricoDeLeituras):
    """Grava cada leitura no InfluxDB com a tag device = id da torre.

    Sem as variaveis INFLUX_* configuradas, nao faz nada (e avisa uma vez).
    """

    def __init__(self):
        self._avisado = False

    def registrar(self, torre_id: str, dados: Dict[str, Any]) -> None:
        try:
            from app.infrastructure.persistence import influx
            if influx.client is None:
                if not self._avisado:
                    logger.info("InfluxDB não configurado; histórico desligado.")
                    self._avisado = True
                return
            influx.write_sensor_reading(dados, device=torre_id)
        except Exception:
            logger.warning("Falha ao gravar no InfluxDB (torre %s)", torre_id, exc_info=True)
