from fastapi import APIRouter

from app.core.config import MQTT_PREFIXO

router = APIRouter(tags=["Geral"])


@router.get("/")
def home():
    return {
        "message":   "Backend Hidropônica rodando",
        "mqttTopic": f"{MQTT_PREFIXO}/<torre_id>/sensores",
    }
