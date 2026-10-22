import asyncio
import logging
from typing import Any, Dict, Iterable, Optional, Set

from fastapi import WebSocket

from app.application.ports.notificador import Notificador

logger = logging.getLogger(__name__)


class WebSocketNotificador(Notificador):
    """Cada conexao diz quais torres acompanha; so recebe dados delas."""

    def __init__(self):
        self._clientes: Dict[WebSocket, Set[str]] = {}
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

    def definir_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._event_loop = loop

    def registrar(self, websocket: WebSocket, torres: Iterable[str]) -> None:
        self._clientes[websocket] = set(torres)

    def remover(self, websocket: WebSocket) -> None:
        self._clientes.pop(websocket, None)

    def notificar(self, torre_id: str, payload: Dict[str, Any]) -> None:
        if self._event_loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._transmitir(torre_id, payload), self._event_loop)

    async def _transmitir(self, torre_id: str, payload: Dict[str, Any]) -> None:
        desconectados = []
        for websocket, torres in list(self._clientes.items()):
            if torre_id not in torres:
                continue
            try:
                await websocket.send_json(payload)
            except Exception:
                desconectados.append(websocket)
        for websocket in desconectados:
            self.remover(websocket)
