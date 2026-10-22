from app.application.ports.estado_monitoramento import EstadoDeMonitoramento
from app.domain.entities.leitura import LeituraAvaliada
from app.domain.exceptions import NenhumDadoDisponivel


class ObterUltimaLeitura:
    def __init__(self, estado: EstadoDeMonitoramento):
        self._estado = estado

    def executar(self, torre_id: str) -> LeituraAvaliada:
        leitura = self._estado.ultima_leitura(torre_id)
        if leitura is None:
            raise NenhumDadoDisponivel("Nenhum dado recebido ainda desta torre.")
        return leitura
