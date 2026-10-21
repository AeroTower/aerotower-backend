from app.application.ports.estado_monitoramento import EstadoDeMonitoramento
from app.domain.entities.leitura import StatusMotor
from app.domain.exceptions import NenhumDadoDisponivel


class ObterStatusMotor:
    def __init__(self, estado: EstadoDeMonitoramento):
        self._estado = estado

    def executar(self, torre_id: str) -> StatusMotor:
        status = self._estado.ultimo_status_motor(torre_id)
        if status is None:
            raise NenhumDadoDisponivel("Nenhum status do motor recebido ainda desta torre.")
        return status
