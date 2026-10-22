import logging
from datetime import datetime
from typing import Any, Dict

from app.application.ports.estado_monitoramento import EstadoDeMonitoramento
from app.application.ports.notificador import Notificador
from app.domain.entities.leitura import StatusMotor

logger = logging.getLogger(__name__)


class ProcessarStatusMotor:
    def __init__(self, estado: EstadoDeMonitoramento, notificador: Notificador):
        self._estado = estado
        self._notificador = notificador

    def executar(self, torre_id: str, dados: Dict[str, Any]) -> StatusMotor:
        status = StatusMotor(bruto=dados, recebido_em=datetime.now())
        self._estado.salvar_status_motor(torre_id, status)
        logger.info("Motor status [%s]: %s", torre_id, dados)

        self._notificador.notificar(torre_id, {
            "torreId":     torre_id,
            "motorStatus": {**status.bruto, "recebidoEm": status.recebido_em.isoformat()},
        })
        return status
