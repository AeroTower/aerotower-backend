from fastapi import APIRouter, Depends

from app.application.use_cases.atualizar_thresholds import AtualizarThresholds
from app.application.use_cases.obter_thresholds import ObterThresholds
from app.core.config import TORRE_LEGADA
from app.presentation.deps import get_atualizar_thresholds, get_obter_thresholds
from app.presentation.schemas.thresholds import ThresholdsUpdate

# Legado: thresholds da TORRE_LEGADA. Use /torres/{id}/thresholds.
router = APIRouter(tags=["Legado (torre única)"], deprecated=True)


@router.get("/thresholds")
def get_thresholds(caso_de_uso: ObterThresholds = Depends(get_obter_thresholds)):
    return caso_de_uso.executar(TORRE_LEGADA).to_dict()


@router.post("/thresholds")
def atualizar_thresholds(
    novos_thresholds: ThresholdsUpdate,
    caso_de_uso: AtualizarThresholds = Depends(get_atualizar_thresholds),
):
    thresholds = caso_de_uso.executar(
        TORRE_LEGADA, novos_thresholds.model_dump(exclude_none=True)
    )
    return {
        "message":    "Thresholds atualizados com sucesso",
        "thresholds": thresholds.to_dict(),
    }
