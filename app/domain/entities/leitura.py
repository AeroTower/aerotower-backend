from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class LeituraSensores:
    bruto: Dict[str, Any] = field(default_factory=dict)
    recebido_em: Optional[datetime] = None

    @property
    def ph(self) -> Optional[float]:
        return self._valor("ph")

    @property
    def ec(self) -> Optional[float]:
        # O firmware mede TDS em ppm; EC (mS/cm) ~= TDS / 500.
        ec = self._valor("ec")
        if ec is None and self._valor("tds") is not None:
            ec = round(self._valor("tds") / 500.0, 2)
        return ec

    @property
    def temperatura_agua(self) -> Optional[float]:
        return self._valor("temperaturaAgua")

    @property
    def temperatura_ambiente(self) -> Optional[float]:
        # "temperatura"/"umidade" sao os nomes do firmware antigo (SHT3x).
        return self._primeiro("temperaturaAmbiente", "temperatura")

    @property
    def umidade_relativa(self) -> Optional[float]:
        return self._primeiro("umidadeRelativa", "umidade")

    @property
    def nivel_agua(self) -> Optional[float]:
        return self._valor("nivelAgua")

    def _valor(self, chave: str) -> Optional[float]:
        valor = self.bruto.get(chave)
        if isinstance(valor, bool):
            return None
        return valor if isinstance(valor, (int, float)) else None

    def _primeiro(self, *chaves: str) -> Optional[float]:
        for chave in chaves:
            valor = self._valor(chave)
            if valor is not None:
                return valor
        return None


@dataclass
class LeituraAvaliada:
    leitura: LeituraSensores
    alertas: List[str] = field(default_factory=list)


@dataclass
class StatusMotor:
    bruto: Dict[str, Any] = field(default_factory=dict)
    recebido_em: Optional[datetime] = None


@dataclass
class ComandoMotor:
    acao: str
    minutos_ligado: Optional[int] = None
    minutos_desligado: Optional[int] = None

    def to_payload(self) -> Dict[str, Any]:
        if self.acao == "ciclo":
            return {
                "acao":              "ciclo",
                "minutos_ligado":    self.minutos_ligado,
                "minutos_desligado": self.minutos_desligado,
            }
        return {"acao": self.acao}
