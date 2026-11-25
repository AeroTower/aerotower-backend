from typing import Optional

from app.application.ports.estado_monitoramento import EstadoDeMonitoramento
from app.application.ports.publicador_comandos import PublicadorDeComandos
from app.application.use_cases.desligar_motor import exigir_torre_online
from app.domain.entities.leitura import ComandoMotor


class IniciarCicloMotor:
    def __init__(self, publicador: PublicadorDeComandos, estado: Optional[EstadoDeMonitoramento] = None):
        self._publicador = publicador
        self._estado = estado

    def executar(self, torre_id: str, minutos_ligado: int, minutos_desligado: int) -> ComandoMotor:
        exigir_torre_online(self._estado, torre_id)
        comando = ComandoMotor(
            acao="ciclo",
            minutos_ligado=minutos_ligado,
            minutos_desligado=minutos_desligado,
        )
        self._publicador.publicar(torre_id, comando)
        return comando
