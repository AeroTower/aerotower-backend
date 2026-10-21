import json
import logging

import paho.mqtt.client as mqtt

from app.application.ports.publicador_comandos import PublicadorDeComandos
from app.domain.entities.leitura import ComandoMotor
from app.domain.exceptions import FalhaNaPublicacao
from app.infrastructure.messaging import topicos

logger = logging.getLogger(__name__)


class MqttPublicador(PublicadorDeComandos):
    def __init__(self, cliente: mqtt.Client):
        self._cliente = cliente

    def publicar(self, torre_id: str, comando: ComandoMotor) -> None:
        destino = topicos.topico(torre_id, topicos.MOTOR_COMANDO)
        payload = json.dumps(comando.to_payload())
        resultado = self._cliente.publish(destino, payload, qos=1)
        if resultado.rc != mqtt.MQTT_ERR_SUCCESS:
            raise FalhaNaPublicacao(resultado.rc)
        logger.info("Publicado [%s]: %s", destino, payload)
