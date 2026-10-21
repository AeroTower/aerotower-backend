from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status

from app.core.config import TORRE_LEGADA
from app.domain.exceptions import NaoAutenticado
from app.infrastructure.notifications.websocket_notificador import WebSocketNotificador
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.sqlalchemy_torre_repository import SqlAlchemyTorreRepository
from app.presentation.deps import get_notificador, usuario_do_token

router = APIRouter()


@router.websocket("/ws/sensores")
async def websocket_sensores(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="Token de sessão (navegador não manda header no WebSocket)"),
    torre: Optional[str] = Query(None, description="Acompanhar só esta torre"),
    notificador: WebSocketNotificador = Depends(get_notificador),
):
    """Leituras em tempo real.

    * com `token`: recebe só as torres da pessoa (ou só `torre`, se for dela);
    * sem `token`: comportamento antigo, só a TORRE_LEGADA (transição).

    Cada mensagem traz `torreId`.
    """
    if token:
        try:
            usuario_id = usuario_do_token(token)
        except NaoAutenticado:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        with SessionLocal() as sessao:
            minhas = {t.id for t in SqlAlchemyTorreRepository(sessao).listar_do_dono(usuario_id)}
        torres = {torre.upper()} & minhas if torre else minhas
    else:
        torres = {TORRE_LEGADA}

    await websocket.accept()
    notificador.registrar(websocket, torres)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        notificador.remover(websocket)
