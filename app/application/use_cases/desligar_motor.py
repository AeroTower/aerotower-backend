from app.application.ports.publicador_comandos import PublicadorDeComandos
from app.domain.entities.leitura import ComandoMotor


class DesligarMotor:
    def __init__(self, publicador: PublicadorDeComandos):
        self._publicador = publicador

    def executar(self, torre_id: str) -> ComandoMotor:
        comando = ComandoMotor(acao="desligar")
        self._publicador.publicar(torre_id, comando)
        return comando
