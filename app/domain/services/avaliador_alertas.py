"""Compara uma leitura com os limites da torre e gera os alertas.

Antes era uma escada de 13 ``if`` (complexidade ciclomatica 15). Agora
cada alerta e uma linha da tabela ``REGRAS``: um sensor novo entra sem
mexer no metodo (principio aberto/fechado).
"""
import operator
from dataclasses import dataclass
from typing import Callable, List, Sequence

from app.domain.entities.leitura import LeituraSensores
from app.domain.entities.thresholds import Thresholds


@dataclass(frozen=True)
class RegraDeAlerta:
    campo: str                              # atributo da LeituraSensores
    limite: str                             # atributo dos Thresholds
    fora_do_limite: Callable[[float, float], bool]
    mensagem: str                           # "{valor}" vira a leitura


ABAIXO = operator.lt
ACIMA = operator.gt

REGRAS: Sequence[RegraDeAlerta] = (
    RegraDeAlerta("ph", "ph_min", ABAIXO, "pH abaixo do limite: {valor}"),
    RegraDeAlerta("ph", "ph_max", ACIMA, "pH acima do limite: {valor}"),
    RegraDeAlerta("ec", "ec_min", ABAIXO, "EC abaixo do limite: {valor}"),
    RegraDeAlerta("ec", "ec_max", ACIMA, "EC acima do limite: {valor}"),
    RegraDeAlerta("temperatura_agua", "temperatura_agua_max", ACIMA, "Temperatura da água alta: {valor}°C"),
    RegraDeAlerta("temperatura_ambiente", "temperatura_ambiente_max", ACIMA, "Temperatura ambiente alta: {valor}°C"),
    RegraDeAlerta("umidade_relativa", "umidade_relativa_min", ABAIXO, "Umidade relativa baixa: {valor}%"),
    RegraDeAlerta("nivel_agua", "nivel_agua_min", ABAIXO, "Nível de água baixo: {valor}%"),
)


@dataclass(frozen=True)
class FaixaFisica:
    """O que o sensor consegue medir. Fora disso o problema e o sensor, nao a agua."""
    campo: str
    minimo: float
    maximo: float
    mensagem: str


FAIXAS_FISICAS: Sequence[FaixaFisica] = (
    FaixaFisica("ph", 0, 14, "Sensor de pH com leitura inválida (confira a sonda): {valor}"),
    FaixaFisica("umidade_relativa", 0, 100, "Sensor de umidade com leitura inválida (confira o sensor): {valor}%"),
    FaixaFisica("nivel_agua", 0, 100, "Sensor de nível com leitura inválida (confira o sensor): {valor}%"),
)


class AvaliadorDeAlertas:
    def __init__(self, regras: Sequence[RegraDeAlerta] = REGRAS,
                 faixas: Sequence[FaixaFisica] = FAIXAS_FISICAS):
        self._regras = regras
        self._faixas = faixas

    def avaliar(self, leitura: LeituraSensores, thresholds: Thresholds) -> List[str]:
        alertas, sensores_com_defeito = self._sensores_com_defeito(leitura)
        for regra in self._regras:
            valor = getattr(leitura, regra.campo)
            # Sensor ausente (None) nao gera alerta: falta de leitura nao e leitura ruim.
            # Leitura impossivel ja virou alerta de sensor: nao manda corrigir a agua.
            if valor is None or regra.campo in sensores_com_defeito:
                continue
            if regra.fora_do_limite(valor, getattr(thresholds, regra.limite)):
                alertas.append(regra.mensagem.format(valor=valor))
        return alertas

    def _sensores_com_defeito(self, leitura: LeituraSensores):
        alertas: List[str] = []
        campos = set()
        for faixa in self._faixas:
            valor = getattr(leitura, faixa.campo)
            if valor is not None and not faixa.minimo <= valor <= faixa.maximo:
                alertas.append(faixa.mensagem.format(valor=valor))
                campos.add(faixa.campo)
        return alertas, campos
