import csv
import io as _io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.application.use_cases.obter_resumo_validacao import (
    ExportarEventos,
    ListarInteresses,
    ObterResumoValidacao,
)
from app.application.use_cases.registrar_evento import RegistrarEvento
from app.application.use_cases.registrar_interesse import RegistrarInteresse
from app.presentation.deps import (
    exigir_admin,
    get_exportar_eventos,
    get_listar_interesses,
    get_obter_resumo_validacao,
    get_registrar_evento,
    get_registrar_interesse,
)
from app.presentation.schemas.evento import (
    EventoCreate,
    EventoExportResponse,
    InteresseCreate,
    InteresseResponse,
    ResumoResponse,
)

router = APIRouter(prefix="/eventos", tags=["Validação"])


@router.post("", status_code=201, summary="Registra um clique de CTA")
def registrar_evento(
    body: EventoCreate,
    caso_de_uso: RegistrarEvento = Depends(get_registrar_evento),
):
    caso_de_uso.executar(body.nome, body.pagina, body.sessao)
    return {"sucesso": True}


@router.post(
    "/interesse",
    status_code=201,
    summary="Registra quem deixou e-mail dizendo o produto que quer",
)
def registrar_interesse(
    body: InteresseCreate,
    caso_de_uso: RegistrarInteresse = Depends(get_registrar_interesse),
):
    caso_de_uso.executar(body.email, body.produto, body.sessao)
    return {"sucesso": True, "mensagem": "Interesse registrado. Obrigado!"}


@router.get(
    "/resumo",
    response_model=ResumoResponse,
    summary="Números da validação: cliques por CTA e total de interessados",
)
def obter_resumo(
    caso_de_uso: ObterResumoValidacao = Depends(get_obter_resumo_validacao),
):
    return caso_de_uso.executar()


@router.get(
    "/interesses",
    dependencies=[Depends(exigir_admin)],
    response_model=list[InteresseResponse],
    summary="Lista os e-mails deixados",
)
def listar_interesses(
    caso_de_uso: ListarInteresses = Depends(get_listar_interesses),
):
    return caso_de_uso.executar()


@router.get(
    "/exportar",
    dependencies=[Depends(exigir_admin)],
    response_model=list[EventoExportResponse],
    summary="Linhas cruas dos cliques, com a sessão",
)
def exportar_eventos(
    caso_de_uso: ExportarEventos = Depends(get_exportar_eventos),
):
    """Use isto, e não o /resumo, para juntar várias coletas.

    Somar o `sessoes` de dois resumos conta duas vezes quem visitou nas
    duas janelas; com as linhas cruas dá para remover a duplicata pelo id
    de sessão.
    """
    return caso_de_uso.executar()


@router.get(
    "/exportar.csv",
    dependencies=[Depends(exigir_admin)],
    summary="Mesmos dados em CSV, para abrir na planilha",
)
def exportar_eventos_csv(
    caso_de_uso: ExportarEventos = Depends(get_exportar_eventos),
):
    buffer = _io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(["id", "evento", "pagina", "sessao", "criado_em"])
    for e in caso_de_uso.executar():
        escritor.writerow([
            e.id,
            e.nome,
            e.pagina,
            e.sessao,
            e.criado_em.isoformat() if e.criado_em else "",
        ])
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="eventos.csv"'
        },
    )
