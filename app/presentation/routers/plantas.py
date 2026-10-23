from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.application.use_cases.buscar_planta import BuscarPlanta
from app.application.use_cases.criar_planta import CriarPlanta
from app.application.use_cases.deletar_planta import DeletarPlanta
from app.application.use_cases.listar_plantas import ListarPlantas
from app.presentation.deps import (
    get_buscar_planta,
    get_criar_planta,
    get_deletar_planta,
    get_listar_plantas,
)
from app.presentation.schemas.planta import PlantaResponse

# Legado: so as plantas antigas, sem torre (sem login). O app usa
# /torres/{id}/plantas. Apagar junto com as outras rotas legadas.
router = APIRouter(prefix="/plantas", tags=["Legado (torre única)"], deprecated=True)


@router.get("", response_model=list[PlantaResponse], summary="Lista todas as plantas")
def listar_plantas(caso_de_uso: ListarPlantas = Depends(get_listar_plantas)):
    return caso_de_uso.executar()


@router.post(
    "",
    response_model=PlantaResponse,
    status_code=201,
    summary="Cadastra uma nova planta",
)
async def criar_planta(
    nome:         str        = Form(...),
    tipo:         str        = Form(...),
    data_plantio: str        = Form(...),
    foto:         UploadFile = File(None),
    caso_de_uso:  CriarPlanta = Depends(get_criar_planta),
):
    nome_arquivo = foto.filename if foto else None
    conteudo = await foto.read() if foto and foto.filename else None
    return await caso_de_uso.executar(nome, tipo, data_plantio, nome_arquivo, conteudo)


@router.delete("/{planta_id}", summary="Remove uma planta")
def deletar_planta(
    planta_id: int,
    caso_de_uso: DeletarPlanta = Depends(get_deletar_planta),
):
    nome = caso_de_uso.executar(planta_id)
    return {
        "sucesso":  True,
        "mensagem": f"Planta '{nome}' removida com sucesso",
    }


@router.get(
    "/{planta_id}",
    response_model=PlantaResponse,
    summary="Busca planta por ID",
)
def buscar_planta(
    planta_id: int,
    caso_de_uso: BuscarPlanta = Depends(get_buscar_planta),
):
    return caso_de_uso.executar(planta_id)
