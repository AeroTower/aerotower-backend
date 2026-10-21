import threading
import time
from typing import Dict, List, Optional, Tuple

from app.application.ports.catalogo_torres import CatalogoDeTorres
from app.core.config import TORRE_LEGADA
from app.domain.entities.kit import Kit, capacidades_do_kit
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import TorreModel


class CatalogoSqlAlchemy(CatalogoDeTorres):
    """Kit de cada torre, com cache curto.

    Roda na thread do MQTT, uma consulta por mensagem seria desperdicio:
    com 100 torres publicando a cada 5 s sao 20 consultas por segundo so
    para descobrir algo que quase nunca muda.
    """

    def __init__(self, validade_s: float = 60.0):
        self._validade_s = validade_s
        self._cache: Dict[str, Tuple[float, Optional[List[str]]]] = {}
        self._lock = threading.Lock()

    def capacidades(self, torre_id: str) -> Optional[List[str]]:
        if torre_id == TORRE_LEGADA:
            # A torre do prototipo tem todos os sensores.
            return capacidades_do_kit(Kit.PRO)

        agora = time.monotonic()
        with self._lock:
            em_cache = self._cache.get(torre_id)
            if em_cache and agora - em_cache[0] < self._validade_s:
                return em_cache[1]

        with SessionLocal() as sessao:
            modelo = sessao.get(TorreModel, torre_id)
            resultado = capacidades_do_kit(Kit(modelo.kit)) if modelo else None

        with self._lock:
            self._cache[torre_id] = (agora, resultado)
        return resultado

    def esquecer(self, torre_id: str) -> None:
        with self._lock:
            self._cache.pop(torre_id, None)
