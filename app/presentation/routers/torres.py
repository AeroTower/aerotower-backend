"""Rotas por torre. Todas exigem login e checam se a torre e de quem pediu.

O vinculo (POST /torre/vincular) fica no servico de autenticacao; aqui
chega pronto, pelo worker.
"""
from typing import List

from fastapi import APIRouter, Depends

from app.application.use_cases.consultar_torres import ListarMinhasTorres
from app.domain.entities.torre import Torre
from app.presentation.deps import (
    container,
    get_listar_minhas_torres,
    get_torre_do_usuario,
    get_usuario_id,
)
from app.presentation.schemas.motor import ComandoCiclo
from app.presentation.schemas.thresholds import ThresholdsUpdate
from app.presentation.schemas.torre import TorreResponse

router = APIRouter(prefix="/torres", tags=["Torres"])


def para_resposta(torre: Torre) -> TorreResponse:
    presenca = container.estado.presenca(torre.id)
    leitura = container.estado.ultima_leitura(torre.id)
    return TorreResponse(
        id=torre.id,
        apelido=torre.apelido,
        kit=torre.kit,
        capacidades=torre.capacidades,
        online=presenca.online,
        firmware=presenca.info.get("firmware"),
        ultimaLeituraEm=leitura.leitura.recebido_em if leitura else None,
        ativadaEm=torre.ativada_em,
    )


@router.get("", response_model=List[TorreResponse], summary="Minhas torres")
def listar(
    usuario_id: str = Depends(get_usuario_id),
    caso_de_uso: ListarMinhasTorres = Depends(get_listar_minhas_torres),
):
    return [para_resposta(t) for t in caso_de_uso.executar(usuario_id)]


@router.get("/{torre_id}", response_model=TorreResponse, summary="Detalhe de uma torre")
def detalhe(torre: Torre = Depends(get_torre_do_usuario)):
    return para_resposta(torre)


# ── Sensores ─────────────────────────────

@router.get("/{torre_id}/dados", summary="Última leitura da torre")
def dados(torre: Torre = Depends(get_torre_do_usuario)):
    avaliada = container.obter_ultima_leitura.executar(torre.id)
    return {
        "torreId":     torre.id,
        "capacidades": torre.capacidades,
        "dados":       avaliada.leitura.bruto,
        "alertas":     avaliada.alertas,
        "recebidoEm":  avaliada.leitura.recebido_em.isoformat(),
    }


@router.get("/{torre_id}/alertas")
def alertas(torre: Torre = Depends(get_torre_do_usuario)):
    return {"alertas": container.obter_alertas.executar(torre.id)}


# ── Thresholds ───────────────────────────

@router.get("/{torre_id}/thresholds")
def get_thresholds(torre: Torre = Depends(get_torre_do_usuario)):
    return container.obter_thresholds.executar(torre.id).to_dict()


@router.post("/{torre_id}/thresholds")
def atualizar_thresholds(body: ThresholdsUpdate, torre: Torre = Depends(get_torre_do_usuario)):
    thresholds = container.atualizar_thresholds.executar(
        torre.id, body.model_dump(exclude_none=True)
    )
    return {"message": "Thresholds atualizados com sucesso", "thresholds": thresholds.to_dict()}


# ── Motor ────────────────────────────────

@router.post("/{torre_id}/motor/ciclo", summary="Inicia ciclo automático da bomba")
def iniciar_ciclo(body: ComandoCiclo, torre: Torre = Depends(get_torre_do_usuario)):
    comando = container.iniciar_ciclo_motor.executar(
        torre.id, body.minutos_ligado, body.minutos_desligado
    )
    return {
        "sucesso":  True,
        "mensagem": f"Ciclo iniciado: {body.minutos_ligado} min ligado / {body.minutos_desligado} min desligado",
        "comando":  comando.to_payload(),
    }


@router.post("/{torre_id}/motor/desligar", summary="Para a bomba imediatamente")
def desligar(torre: Torre = Depends(get_torre_do_usuario)):
    comando = container.desligar_motor.executar(torre.id)
    return {"sucesso": True, "mensagem": "Motor desligado", "comando": comando.to_payload()}


@router.get("/{torre_id}/motor/status", summary="Último status da bomba")
def status_motor(torre: Torre = Depends(get_torre_do_usuario)):
    status = container.obter_status_motor.executar(torre.id)
    return {**status.bruto, "recebidoEm": status.recebido_em.isoformat()}
