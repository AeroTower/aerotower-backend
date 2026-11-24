"""CT-ACEIT-02 (teste individual) — Sonda de pH com defeito.

Historia: "Como dono, quero saber quando a leitura de pH e impossivel,
para trocar a sonda em vez de colocar produto na agua a toa."
O pH so existe de 0 a 14. Fora disso, e a sonda (solta, em curto ou sem
calibracao), nao a agua. O proprio firmware classifica esse caso como
"leitura_invalida", mas o Backend ignora essa informacao.
Obtido em 24/11/2026 (antes da correcao): o painel mostra "pH abaixo do limite: -3.2" (ou "acima: 21.4"),
e o dono e levado a corrigir uma agua que pode estar perfeita.

Corrigido na refatoracao: o teste passou a fazer parte da suite normal e
protege contra a volta do defeito.
"""
import uuid

from pytest_bdd import given, parsers, scenarios, then, when

from tests.apoio import publicar, torre_de

scenarios("sonda_ph_com_defeito.feature")


@given(parsers.parse('que a Maria tem uma torre do kit "{kit}" vinculada à conta dela'),
       target_fixture="cenario")
def maria_tem_torre(app_e_mqtt, kit):
    cliente, _, container = app_e_mqtt
    torre, h = torre_de(cliente, f"maria-{uuid.uuid4().hex[:6]}", kit=kit)
    return {"cliente": cliente, "container": container, "torre": torre, "maria": h}


@when(parsers.parse("a torre publica pH {ph:g} e nível de água {nivel:g}"))
def torre_publica(cenario, ph, nivel):
    publicar(cenario["container"], f"aerotower/{cenario['torre']}/sensores",
             {"ph": ph, "nivelAgua": nivel})


def _alertas(cenario):
    return cenario["cliente"].get(f"/torres/{cenario['torre']}/alertas",
                                  headers=cenario["maria"]).json()["alertas"]


@then("o painel da Maria avisa que o sensor de pH está com defeito")
def avisa_defeito(cenario):
    alertas = _alertas(cenario)
    assert any("sensor de ph" in a.lower() for a in alertas), f"alertas: {alertas}"


@then("o painel da Maria não manda corrigir o pH da água")
def nao_manda_corrigir(cenario):
    alertas = _alertas(cenario)
    assert not any(a.startswith(("pH abaixo", "pH acima")) for a in alertas), f"alertas: {alertas}"
