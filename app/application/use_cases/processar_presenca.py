import logging
from datetime import datetime
from typing import Any, Dict

from app.application.ports.estado_monitoramento import EstadoDeMonitoramento
from app.application.ports.notificador import Notificador
from app.domain.entities.presenca import Presenca

logger = logging.getLogger(__name__)


class ProcessarPresenca:
    """Trata os topicos status (online/offline) e info (firmware, sensores)."""

    def __init__(self, estado: EstadoDeMonitoramento, notificador: Notificador):
        self._estado = estado
        self._notificador = notificador

    def executar(self, torre_id: str, tipo: str, dados: Dict[str, Any]) -> Presenca:
        presenca = self._estado.presenca(torre_id)
        if tipo == "status":
            presenca.online = str(dados.get("status", "")).lower() == "online"
        elif tipo == "info":
            presenca.info = dict(dados)
        presenca.atualizado_em = datetime.now()

        logger.info("Presença [%s] %s: %s", torre_id, tipo, dados)
        self._notificador.notificar(torre_id, {
            "torreId": torre_id,
            "online":  presenca.online,
        })
        return presenca
