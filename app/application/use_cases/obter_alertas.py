from typing import List

from app.application.ports.estado_monitoramento import EstadoDeMonitoramento


class ObterAlertas:
    def __init__(self, estado: EstadoDeMonitoramento):
        self._estado = estado

    def executar(self, torre_id: str) -> List[str]:
        leitura = self._estado.ultima_leitura(torre_id)
        return leitura.alertas if leitura is not None else []
