import json
from datetime import datetime
from typing import Optional

import redis

from app.application.ports.estado_monitoramento import EstadoDeMonitoramento
from app.domain.entities.leitura import LeituraAvaliada, LeituraSensores, StatusMotor
from app.domain.entities.thresholds import Thresholds

CHAVE_LEITURA    = "aerotower:leitura"
CHAVE_MOTOR      = "aerotower:motor"
CHAVE_THRESHOLDS = "aerotower:thresholds"


def _data_para_texto(data: Optional[datetime]) -> Optional[str]:
    return data.isoformat() if data else None


def _texto_para_data(texto: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(texto) if texto else None


class EstadoRedis(EstadoDeMonitoramento):
    def __init__(self, url: str):
        self._r = redis.from_url(url, decode_responses=True)
        self._r.ping()

        # Thresholds: carrega uma vez e mantém em memória também
        self._thresholds = Thresholds()
        salvo = self._r.get(CHAVE_THRESHOLDS)
        if salvo:
            self._thresholds.aplicar(json.loads(salvo))

    # ── Leitura dos sensores ──────────────
    def salvar_leitura(self, leitura: LeituraAvaliada) -> None:
        self._r.set(CHAVE_LEITURA, json.dumps({
            "bruto":       leitura.leitura.bruto,
            "recebido_em": _data_para_texto(leitura.leitura.recebido_em),
            "alertas":     leitura.alertas,
        }))

    def ultima_leitura(self) -> Optional[LeituraAvaliada]:
        salvo = self._r.get(CHAVE_LEITURA)
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
    def salvar_status_motor(self, status: StatusMotor) -> None:
        self._r.set(CHAVE_MOTOR, json.dumps({
            "bruto":       status.bruto,
            "recebido_em": _data_para_texto(status.recebido_em),
        }))

    def ultimo_status_motor(self) -> Optional[StatusMotor]:
        salvo = self._r.get(CHAVE_MOTOR)
        if not salvo:
            return None
        d = json.loads(salvo)
        return StatusMotor(
            bruto=d["bruto"],
            recebido_em=_texto_para_data(d["recebido_em"]),
        )

    # ── Thresholds ────────────────────────
    def thresholds(self) -> Thresholds:
        return self._thresholds

    def salvar_thresholds(self, thresholds: Thresholds) -> None:
        self._r.set(CHAVE_THRESHOLDS, json.dumps(thresholds.to_dict()))