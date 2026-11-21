"""Testes de aceitacao (BDD): os criterios de aceite da historia de usuario,
escritos em portugues no arquivo .feature e executados contra o Backend.
"""
import json
import uuid

from pytest_bdd import given, parsers, scenarios, then, when

from tests.apoio import cabecalho, publicar, torre_de

scenarios("monitorar_torre.feature")


@given(parsers.parse('que a Maria tem uma torre do kit "{kit}" vinculada à conta dela'),
       target_fixture="cenario")
def maria_tem_torre(app_e_mqtt, kit):
    cliente, mqtt, container = app_e_mqtt
    maria = f"maria-{uuid.uuid4().hex[:6]}"      # uma Maria nova por cenario
    torre, h = torre_de(cliente, maria, kit=kit)
    return {"cliente": cliente, "mqtt": mqtt, "container": container, "torre": torre,
            "maria": h, "maria_id": maria}


@given(parsers.parse('que a Maria também tem uma torre do kit "{kit}"'))
def maria_tem_torre_basica(cenario, kit):
    cenario["basica"], _ = torre_de(cenario["cliente"], cenario["maria_id"], kit=kit)


@when(parsers.parse("a torre publica pH {ph:g} e nível de água {nivel:g}"))
def torre_publica(cenario, ph, nivel):
    publicar(cenario["container"], f"aerotower/{cenario['torre']}/sensores",
             {"ph": ph, "nivelAgua": nivel})


@when(parsers.parse("a torre básica publica pH {ph:g} e o motor ligado"))
def basica_publica(cenario, ph):
    publicar(cenario["container"], f"aerotower/{cenario['basica']}/sensores",
             {"ph": ph, "motor": True})


@when(parsers.parse("a Maria pede um ciclo de {ligado:d} minutos ligada e {desligado:d} desligada"))
def maria_pede_ciclo(cenario, ligado, desligado):
    r = cenario["cliente"].post(f"/torres/{cenario['torre']}/motor/ciclo", headers=cenario["maria"],
                                json={"minutos_ligado": ligado, "minutos_desligado": desligado})
    assert r.status_code == 200


@when("o João tenta abrir o painel da torre da Maria")
def joao_tenta(cenario):
    cenario["resposta"] = cenario["cliente"].get(f"/torres/{cenario['torre']}/dados",
                                                 headers=cabecalho("joao"))


def _painel(cenario, torre):
    r = cenario["cliente"].get(f"/torres/{torre}/dados", headers=cenario["maria"])
    assert r.status_code == 200
    return r.json()


@then(parsers.parse('o painel da Maria mostra o alerta "{trecho}"'))
def mostra_alerta(cenario, trecho):
    assert any(trecho in a for a in _painel(cenario, cenario["torre"])["alertas"])


@then("o painel da Maria não mostra nenhum alerta")
def sem_alerta(cenario):
    assert _painel(cenario, cenario["torre"])["alertas"] == []


@then(parsers.parse("a torre recebe o comando de ciclo com {ligado:d} e {desligado:d} minutos"))
def torre_recebe(cenario, ligado, desligado):
    topico, payload = cenario["mqtt"].publicados[-1]
    assert topico == f"aerotower/{cenario['torre']}/motor/comando"
    assert json.loads(payload) == {"acao": "ciclo", "minutos_ligado": ligado,
                                   "minutos_desligado": desligado}


@then('o João recebe "não encontrada"')
def joao_nao_ve(cenario):
    assert cenario["resposta"].status_code == 404
    assert "não encontrada" in cenario["resposta"].json()["detail"]


@then("o painel da torre básica mostra só os dados da bomba")
def so_bomba(cenario):
    painel = _painel(cenario, cenario["basica"])
    assert painel["capacidades"] == ["bomba"]
    assert painel["dados"] == {"motor": True} and painel["alertas"] == []
