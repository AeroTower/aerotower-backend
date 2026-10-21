"""Rotas da etapa de fabrica. Protegidas por X-Admin-Key (ADMIN_API_KEY).

Quem usa e o script scripts/provisionar_torre.py, nao o app.
"""
from typing import List

from fastapi import APIRouter, Depends

from app.application.use_cases.cadastrar_torre import (
    CadastrarTorre,
    GerarNovoCodigo,
    ListarTodasAsTorres,
)
from app.presentation.deps import (
    container,
    exigir_admin,
    get_cadastrar_torre,
    get_gerar_novo_codigo,
    get_listar_todas_as_torres,
)
from app.presentation.schemas.torre import (
    CadastrarTorreRequest,
    CodigoAtivacaoResponse,
    TorreAdminResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin (fábrica)"], dependencies=[Depends(exigir_admin)])


@router.post("/torres", response_model=CodigoAtivacaoResponse, status_code=201,
             summary="Cadastra uma placa e gera o código do adesivo")
def cadastrar(body: CadastrarTorreRequest, caso_de_uso: CadastrarTorre = Depends(get_cadastrar_torre)):
    torre, codigo = caso_de_uso.executar(body.torreId, body.kit)
    container.catalogo.esquecer(torre.id)
    return CodigoAtivacaoResponse(torreId=torre.id, kit=torre.kit, codigoAtivacao=codigo)


@router.post("/torres/{torre_id}/novo-codigo", response_model=CodigoAtivacaoResponse,
             summary="Desvincula o dono e gera outro código (adesivo perdido, revenda)")
def novo_codigo(torre_id: str, caso_de_uso: GerarNovoCodigo = Depends(get_gerar_novo_codigo)):
    torre, codigo = caso_de_uso.executar(torre_id.upper())
    return CodigoAtivacaoResponse(torreId=torre.id, kit=torre.kit, codigoAtivacao=codigo)


@router.get("/torres", response_model=List[TorreAdminResponse], summary="Todas as torres cadastradas")
def listar(caso_de_uso: ListarTodasAsTorres = Depends(get_listar_todas_as_torres)):
    return [
        TorreAdminResponse(
            id=t.id, kit=t.kit, ativada=t.ativada, donoId=t.dono_id,
            criadaEm=t.criada_em, ativadaEm=t.ativada_em,
        )
        for t in caso_de_uso.executar()
    ]
