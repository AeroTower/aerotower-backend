import json
import threading
from datetime import datetime
from typing import Dict, Optional

import redis

from app.application.ports.estado_monitoramento import EstadoDeMonitoramento
from app.domain.entities.leitura import LeituraAvaliada, LeituraSensores, StatusMotor
from app.domain.entities.presenca import Presenca
from app.domain.entities.thresholds import Thresholds


def _chave(torre_id: str, tipo: str) -> str:
    return f"aerotower:{torre_id}:{tipo}"


def _data_para_texto(data: Optional[datetime]) -> Optional[str]:
    return data.isoformat() if data else None


def _texto_para_data(texto: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(texto) if texto else None


class EstadoRedis(EstadoDeMonitoramento):
    """Mesmo contrato do EstadoEmMemoria, mas guardado no Redis.

    Sobrevive a restart: ultima leitura, status do motor e thresholds.
    Presenca fica em memoria: o broker reenvia os topicos status/info
    (retidos) quando o backend reconecta, entao ela se refaz sozinha.
    """

    def __init__(self, url: str):
        self._r = redis.from_url(url, decode_responses=True)
        self._r.ping()

        self._lock = threading.Lock()
        self._thresholds: Dict[str, Thresholds] = {}
        self._presencas: Dict[str, Presenca] = {}

    # ── Leitura dos sensores ──────────────
    def salvar_leitura(self, torre_id: str, leitura: LeituraAvaliada) -> None:
        self._r.set(_chave(torre_id, "leitura"), json.dumps({
            "bruto":       leitura.leitura.bruto,
            "recebido_em": _data_para_texto(leitura.leitura.recebido_em),
            "alertas":     leitura.alertas,
        }))

    def ultima_leitura(self, torre_id: str) -> Optional[LeituraAvaliada]:
        salvo = self._r.get(_chave(torre_id, "leitura"))
        if not salvo:
            return None
        d = json.loads(salvo)
        return LeituraAvaliada(
            leitura=LeituraSensores(
                bruto=d["bruto"],
                recebido_em=_texto_para_data(d["recebido_em"]),
            ),
            alertas=d["alertas"],
        )

    # ── Status do motor ───────────────────
    def salvar_status_motor(self, torre_id: str, status: StatusMotor) -> None:
        self._r.set(_chave(torre_id, "motor"), json.dumps({
            "bruto":       status.bruto,
            "recebido_em": _data_para_texto(status.recebido_em),
        }))

    def ultimo_status_motor(self, torre_id: str) -> Optional[StatusMotor]:
        salvo = self._r.get(_chave(torre_id, "motor"))
        if not salvo:
            return None
        d = json.loads(salvo)
        return StatusMotor(
            bruto=d["bruto"],
            recebido_em=_texto_para_data(d["recebido_em"]),
        )

    # ── Thresholds ────────────────────────
    def thresholds(self, torre_id: str) -> Thresholds:
        with self._lock:
            if torre_id not in self._thresholds:
                t = Thresholds()
                salvo = self._r.get(_chave(torre_id, "thresholds"))
                if salvo:
                    t.aplicar(json.loads(salvo))
                self._thresholds[torre_id] = t
            return self._thresholds[torre_id]

    def salvar_thresholds(self, torre_id: str, thresholds: Thresholds) -> None:
        self._r.set(_chave(torre_id, "thresholds"), json.dumps(thresholds.to_dict()))

    # ── Presenca (memoria) ────────────────
    def presenca(self, torre_id: str) -> Presenca:
        with self._lock:
            return self._presencas.setdefault(torre_id, Presenca())