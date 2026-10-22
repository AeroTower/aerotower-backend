"""Nomes de topico: um lugar so para montar e para interpretar.

    aerotower/{torre_id}/sensores        torre -> servidor
    aerotower/{torre_id}/motor/status    torre -> servidor (retido)
    aerotower/{torre_id}/motor/comando   servidor -> torre
    aerotower/{torre_id}/status          torre -> servidor (retido; LWT "offline")
    aerotower/{torre_id}/info            torre -> servidor (retido)

O id da torre sai SEMPRE do topico, nunca do payload. Com credencial por
torre no broker (plano Starter: regra aerotower/${mqtt-username}/#), o
topico passa a ser a prova de quem publicou.
"""
from typing import List, Optional, Tuple

from app.core.config import (
    MQTT_PREFIXO,
    TOPIC_MOTOR_COMANDO,
    TOPIC_MOTOR_STATUS,
    TOPIC_SENSORES,
    TORRE_LEGADA,
)
from app.domain.entities.torre import id_de_torre_valido

SENSORES      = "sensores"
MOTOR_STATUS  = "motor/status"
MOTOR_COMANDO = "motor/comando"
STATUS        = "status"
INFO          = "info"

_ENTRADA = (SENSORES, MOTOR_STATUS, STATUS, INFO)


def topico(torre_id: str, tipo: str) -> str:
    if torre_id == TORRE_LEGADA:
        legado = {
            SENSORES: TOPIC_SENSORES,
            MOTOR_STATUS: TOPIC_MOTOR_STATUS,
            MOTOR_COMANDO: TOPIC_MOTOR_COMANDO,
        }.get(tipo)
        if legado:
            return legado
    return f"{MQTT_PREFIXO}/{torre_id}/{tipo}"


def assinaturas() -> List[str]:
    novos = [f"{MQTT_PREFIXO}/+/{tipo}" for tipo in _ENTRADA]
    return novos + [TOPIC_SENSORES, TOPIC_MOTOR_STATUS]


def interpretar(nome: str) -> Optional[Tuple[str, str]]:
    """'aerotower/AT-24DC.../motor/status' -> ('AT-24DC...', 'motor/status')."""
    if nome == TOPIC_SENSORES:
        return TORRE_LEGADA, SENSORES
    if nome == TOPIC_MOTOR_STATUS:
        return TORRE_LEGADA, MOTOR_STATUS

    prefixo = MQTT_PREFIXO + "/"
    if not nome.startswith(prefixo):
        return None
    torre_id, _, tipo = nome[len(prefixo):].partition("/")
    if tipo not in _ENTRADA or not id_de_torre_valido(torre_id):
        return None
    return torre_id, tipo
