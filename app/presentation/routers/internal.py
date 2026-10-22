"""Rotas chamadas por outros servicos, nunca pelo app.

PUT /internal/torres/{id} e usada pelo worker do auth-aerotower (Servico B)
para entregar o estado de cada torre: cadastro de fabrica, vinculo e
desvinculo. Protegida por X-Service-Key.
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.application.use_cases.sincronizar_torre import SincronizarTorre
from app.domain.entities.kit import Kit
from app.presentation.deps import container, exigir_servico, get_sincronizar_torre

router = APIRouter(prefix="/internal", tags=["Interno (serviços)"],
                   dependencies=[Depends(exigir_servico)], include_in_schema=True)


class EstadoTorre(BaseModel):
    kit:     Kit
    donoId:  Optional[str] = None
    apelido: Optional[str] = Field(None, max_length=40)
    versao:  int = Field(..., ge=1)


@router.put("/torres/{torre_id}", summary="Estado de uma torre vindo do serviço de auth")
def sincronizar(torre_id: str, body: EstadoTorre,
                caso_de_uso: SincronizarTorre = Depends(get_sincronizar_torre)):
    aplicado = caso_de_uso.executar(torre_id, body.kit, body.donoId, body.apelido, body.versao)
    container.catalogo.esquecer(torre_id.upper())
    return {"torreId": torre_id.upper(), "aplicado": aplicado}
