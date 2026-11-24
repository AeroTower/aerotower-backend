"""CT-UNIT-02 (teste individual) — Limites de alerta inconsistentes.

Cenario: o dono (ou um bug no app) grava limites impossiveis ou
contraditorios para os alertas da torre.
Esperado: a entidade Thresholds recusa (ValueError) e nada muda.
Obtido em 24/11/2026 (antes da correcao): aceita tudo. Com phMin 8 e phMax 6, TODA leitura de pH gera
alerta ("abaixo" ou "acima"), e o dono deixa de confiar nos avisos.

Corrigido na refatoracao (Thresholds valida faixa e minimo < maximo); o
teste passou a fazer parte da suite normal e protege contra a volta do defeito.
"""
import pytest

from app.domain.entities.thresholds import Thresholds

@pytest.mark.parametrize(
    "novos, motivo",
    [
        ({"phMin": 8, "phMax": 6}, "minimo de pH maior que o maximo"),
        ({"phMax": 20}, "pH so vai de 0 a 14"),
        ({"umidadeRelativaMin": 150}, "umidade relativa so vai de 0 a 100%"),
        ({"nivelAguaMin": -10}, "nivel de agua negativo"),
    ],
    ids=["ph-invertido", "ph-acima-de-14", "umidade-150", "nivel-negativo"],
)
def test_limites_impossiveis_sao_recusados(novos, motivo):
    limites = Thresholds()
    antes = limites.to_dict()

    with pytest.raises(ValueError):
        limites.aplicar(novos)

    assert limites.to_dict() == antes, f"aceitou limite impossivel: {motivo}"
