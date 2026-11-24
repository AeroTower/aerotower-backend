import math
from dataclasses import dataclass, fields
from typing import Any, Dict

from app.domain.exceptions import LimitesInvalidos


@dataclass
class Thresholds:
    ph_min: float = 5.5
    ph_max: float = 6.5
    ec_min: float = 0.8
    ec_max: float = 1.8
    temperatura_agua_max: float = 28
    temperatura_ambiente_max: float = 32
    umidade_relativa_min: float = 45
    nivel_agua_min: float = 35

    _APELIDOS = {
        "ph_min":                  "phMin",
        "ph_max":                  "phMax",
        "ec_min":                  "ecMin",
        "ec_max":                  "ecMax",
        "temperatura_agua_max":    "temperaturaAguaMax",
        "temperatura_ambiente_max": "temperaturaAmbienteMax",
        "umidade_relativa_min":    "umidadeRelativaMin",
        "nivel_agua_min":          "nivelAguaMin",
    }

    # Faixa fisica de cada limite: fora dela o sensor nem consegue medir.
    _FAIXAS = {
        "ph_min":                   (0, 14),
        "ph_max":                   (0, 14),
        "ec_min":                   (0, 20),
        "ec_max":                   (0, 20),
        "temperatura_agua_max":     (0, 50),
        "temperatura_ambiente_max": (-10, 60),
        "umidade_relativa_min":     (0, 100),
        "nivel_agua_min":           (0, 100),
    }
    _PARES = (("ph_min", "ph_max"), ("ec_min", "ec_max"))

    def to_dict(self) -> Dict[str, float]:
        return {self._APELIDOS[f.name]: getattr(self, f.name) for f in fields(self)}

    def aplicar(self, valores: Dict[str, Any]) -> None:
        """Aplica os valores novos; se o resultado for impossivel, nada muda."""
        por_apelido = {apelido: nome for nome, apelido in self._APELIDOS.items()}
        novos = {f.name: getattr(self, f.name) for f in fields(self)}
        for apelido, valor in valores.items():
            nome = por_apelido.get(apelido)
            if nome is not None and valor is not None:
                novos[nome] = valor
        self._validar(novos)
        for nome, valor in novos.items():
            setattr(self, nome, valor)

    def _validar(self, valores: Dict[str, Any]) -> None:
        for nome, (minimo, maximo) in self._FAIXAS.items():
            valor = valores[nome]
            if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
                raise LimitesInvalidos(f"{self._APELIDOS[nome]} precisa ser um número.")
            if not minimo <= valor <= maximo:
                raise LimitesInvalidos(f"{self._APELIDOS[nome]} deve ficar entre {minimo} e {maximo}.")
        for menor, maior in self._PARES:
            if valores[menor] >= valores[maior]:
                raise LimitesInvalidos(
                    f"{self._APELIDOS[menor]} deve ser menor que {self._APELIDOS[maior]}."
                )
