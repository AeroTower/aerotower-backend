from fastapi import APIRouter, Depends

from app.application.use_cases.desligar_motor import DesligarMotor
from app.application.use_cases.iniciar_ciclo_motor import IniciarCicloMotor
from app.application.use_cases.obter_status_motor import ObterStatusMotor
from app.core.config import TORRE_LEGADA
from app.presentation.deps import (
    get_desligar_motor,
    get_iniciar_ciclo_motor,
    get_obter_status_motor,
)
from app.presentation.schemas.motor import ComandoCiclo

# Legado: comanda a TORRE_LEGADA. Use /torres/{id}/motor/...
router = APIRouter(prefix="/motor", tags=["Legado (torre única)"], deprecated=True)


@router.post("/ciclo", summary="Inicia ciclo automático da bomba")
def iniciar_ciclo(
    body: ComandoCiclo,
    caso_de_uso: IniciarCicloMotor = Depends(get_iniciar_ciclo_motor),
):
    comando = caso_de_uso.executar(TORRE_LEGADA, body.minutos_ligado, body.minutos_desligado)
    return {
        "sucesso":  True,
        "mensagem": f"Ciclo iniciado: {body.minutos_ligado} min ligado / {body.minutos_desligado} min desligado",
        "comando":  comando.to_payload(),
    }


@router.post("/desligar", summary="Para o motor imediatamente")
def desligar_motor(caso_de_uso: DesligarMotor = Depends(get_desligar_motor)):
    comando = caso_de_uso.executar(TORRE_LEGADA)
    return {
        "sucesso":  True,
        "mensagem": "Motor desligado",
        "comando":  comando.to_payload(),
    }


@router.get("/status", summary="Último status do motor")
def get_motor_status(caso_de_uso: ObterStatusMotor = Depends(get_obter_status_motor)):
    status = caso_de_uso.executar(TORRE_LEGADA)
    return {**status.bruto, "recebidoEm": status.recebido_em.isoformat()}
