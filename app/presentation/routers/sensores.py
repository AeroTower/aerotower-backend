from fastapi import APIRouter, Depends

from app.application.use_cases.obter_alertas import ObterAlertas
from app.application.use_cases.obter_ultima_leitura import ObterUltimaLeitura
from app.core.config import TORRE_LEGADA
from app.presentation.deps import get_obter_alertas, get_obter_ultima_leitura

# Rotas da TORRE_LEGADA (prototipo), sem login, mantidas so ate o app usar
# /torres/{id}/... Depois disso, apague este arquivo.
router = APIRouter(tags=["Legado (torre única)"], deprecated=True)


@router.get("/dados")
def get_dados(caso_de_uso: ObterUltimaLeitura = Depends(get_obter_ultima_leitura)):
    avaliada = caso_de_uso.executar(TORRE_LEGADA)
    return {
        "dados":      avaliada.leitura.bruto,
        "alertas":    avaliada.alertas,
        "recebidoEm": avaliada.leitura.recebido_em.isoformat(),
    }


@router.get("/alertas")
def get_alertas(caso_de_uso: ObterAlertas = Depends(get_obter_alertas)):
    return {"alertas": caso_de_uso.executar(TORRE_LEGADA)}
