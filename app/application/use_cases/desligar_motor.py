from typing import Optional

from app.application.ports.estado_monitoramento import EstadoDeMonitoramento
from app.application.ports.publicador_comandos import PublicadorDeComandos
from app.domain.entities.leitura import ComandoMotor
from app.domain.exceptions import TorreOffline


def exigir_torre_online(estado: Optional[EstadoDeMonitoramento], torre_id: str) -> None:
    """O comando vai sem "retain" e a torre conecta com sessao limpa: se ela
    avisou que caiu (status "offline"), o broker descartaria o comando e o app
    mostraria um sucesso falso. Torre que nunca mandou status passa (legado)."""
    if estado is not None and estado.presenca(torre_id).online is False:
        raise TorreOffline(torre_id)


class DesligarMotor:
    def __init__(self, publicador: PublicadorDeComandos, estado: Optional[EstadoDeMonitoramento] = None):
        self._publicador = publicador
        self._estado = estado

    def executar(self, torre_id: str) -> ComandoMotor:
        exigir_torre_online(self._estado, torre_id)
        comando = ComandoMotor(acao="desligar")
        self._publicador.publicar(torre_id, comando)
        return comando
