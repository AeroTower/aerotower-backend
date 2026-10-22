import json
import logging

import paho.mqtt.client as mqtt

from app.application.use_cases.processar_leitura import ProcessarLeitura
from app.application.use_cases.processar_presenca import ProcessarPresenca
from app.application.use_cases.processar_status_motor import ProcessarStatusMotor
from app.infrastructure.messaging import topicos

logger = logging.getLogger(__name__)


class MqttSubscriber:
    def __init__(
        self,
        cliente: mqtt.Client,
        processar_leitura: ProcessarLeitura,
        processar_status_motor: ProcessarStatusMotor,
        processar_presenca: ProcessarPresenca,
    ):
        self._cliente = cliente
        self._processar_leitura = processar_leitura
        self._processar_status_motor = processar_status_motor
        self._processar_presenca = processar_presenca

    def registrar(self) -> None:
        self._cliente.on_connect = self._on_connect
        self._cliente.on_message = self._on_message
        self._cliente.on_disconnect = self._on_disconnect

    def _on_connect(self, cliente, userdata, flags, rc):
        if rc == 0:
            logger.info("Backend conectado ao broker MQTT.")
            for filtro in topicos.assinaturas():
                cliente.subscribe(filtro, qos=1)
            logger.info("Inscrito em: %s", ", ".join(topicos.assinaturas()))
        else:
            logger.error("Erro ao conectar no MQTT. Código: %s", rc)

    def _on_message(self, cliente, userdata, msg):
        destino = topicos.interpretar(msg.topic)
        if destino is None:
            logger.debug("Tópico ignorado: %s", msg.topic)
            return
        torre_id, tipo = destino

        try:
            dados = json.loads(msg.payload.decode("utf-8")) if msg.payload else {}
        except (ValueError, UnicodeDecodeError):
            logger.warning("Payload MQTT inválido em %s", msg.topic, exc_info=True)
            return
        if not isinstance(dados, dict):
            logger.warning("Payload MQTT não é objeto JSON em %s", msg.topic)
            return

        try:
            if tipo == topicos.SENSORES:
                self._processar_leitura.executar(torre_id, dados)
            elif tipo == topicos.MOTOR_STATUS:
                self._processar_status_motor.executar(torre_id, dados)
            else:
                self._processar_presenca.executar(torre_id, tipo, dados)
        except Exception:
            logger.error("Erro ao processar mensagem MQTT de %s", msg.topic, exc_info=True)

    def _on_disconnect(self, cliente, userdata, rc):
        logger.warning("MQTT desconectado! Código: %s", rc)
