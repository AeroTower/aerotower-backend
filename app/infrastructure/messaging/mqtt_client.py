import logging

import paho.mqtt.client as mqtt

from app.core.config import BROKER, MQTT_PASS, MQTT_TLS, MQTT_USER, PORT

logger = logging.getLogger(__name__)


def criar_cliente() -> mqtt.Client:
    cliente = mqtt.Client()
    cliente.username_pw_set(MQTT_USER, MQTT_PASS)
    if MQTT_TLS:
        cliente.tls_set()
    return cliente


def conectar(cliente: mqtt.Client) -> bool:
    try:
        logger.info("Iniciando conexão MQTT com %s:%s", BROKER, PORT)
        cliente.connect(BROKER, PORT, 60)
        cliente.loop_start()
        return True
    except Exception:
        logger.error(
            "Não foi possível conectar ao broker MQTT. "
            "A API continua disponível, sem telemetria.",
            exc_info=True,
        )
        return False


def desconectar(cliente: mqtt.Client) -> None:
    try:
        logger.info("Encerrando conexão MQTT...")
        cliente.loop_stop()
        cliente.disconnect()
    except Exception:
        logger.warning("Erro ao encerrar a conexão MQTT.", exc_info=True)
