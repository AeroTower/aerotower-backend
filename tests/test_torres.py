import json
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from tests.conftest import MensagemMqtt

SERVICO = {"X-Service-Key": "servico-teste"}


def _token(usuario_id, segredo="segredo-de-teste", emissor="aerotower-auth", minutos=60):
    """Igual ao que o auth-aerotower emite."""
    agora = datetime.now(timezone.utc)
    return jwt.encode({"sub": usuario_id, "iss": emissor, "aud": "aerotower",
                       "iat": agora, "exp": agora + timedelta(minutes=minutos)},
                      segredo, algorithm="HS256")


def _h(usuario_id, **kw):
    return {"Authorization": f"Bearer {_token(usuario_id, **kw)}"}


def _id_torre():
    return "AT-" + uuid.uuid4().hex[:12].upper()


def _sincronizar(cliente, torre_id, kit="pro", dono=None, versao=1, apelido=None):
    r = cliente.put(f"/internal/torres/{torre_id}", headers=SERVICO,
                    json={"kit": kit, "donoId": dono, "apelido": apelido, "versao": versao})
    assert r.status_code == 200, r.text
    return r.json()


def _publicar(container, topico, dados):
    container.subscriber._on_message(None, None, MensagemMqtt(topico, json.dumps(dados).encode()))


def test_rota_interna_exige_chave(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    corpo = {"kit": "pro", "donoId": "x", "versao": 1}
    assert cliente.put(f"/internal/torres/{_id_torre()}", json=corpo).status_code == 403
    assert cliente.put(f"/internal/torres/{_id_torre()}", json=corpo,
                       headers={"X-Service-Key": "errada"}).status_code == 403


def test_token_falso_ou_de_outro_emissor(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    assert cliente.get("/torres").status_code == 401
    assert cliente.get("/torres", headers=_h("maria", segredo="outro")).status_code == 401
    assert cliente.get("/torres", headers=_h("maria", emissor="alguem")).status_code == 401
    assert cliente.get("/torres", headers=_h("maria", minutos=-5)).status_code == 401


def test_fluxo_e_isolamento(app_e_mqtt):
    cliente, mqtt, container = app_e_mqtt
    torre_id = _id_torre()
    _sincronizar(cliente, torre_id, "pro")                                     # torre.cadastrada
    _sincronizar(cliente, torre_id, "pro", dono="maria", versao=2, apelido="Varanda")  # torre.vinculada
    maria, joao = _h("maria"), _h("joao")

    corpo = cliente.get("/torres", headers=maria).json()
    assert [t["id"] for t in corpo] == [torre_id]
    assert corpo[0]["capacidades"] == ["bomba", "nivel", "ph", "tds", "clima"]
    assert cliente.get("/torres", headers=joao).json() == []

    assert cliente.get(f"/torres/{torre_id}/dados", headers=joao).status_code == 404
    assert cliente.post(f"/torres/{torre_id}/motor/desligar", headers=joao).status_code == 404
    assert mqtt.publicados == []

    _publicar(container, f"aerotower/{torre_id}/sensores",
              {"ph": 7.4, "tds": 600, "temperaturaAmbiente": 24.1, "nivelAgua": 20.0})
    alertas = " ".join(cliente.get(f"/torres/{torre_id}/dados", headers=maria).json()["alertas"])
    assert "pH acima" in alertas and "Nível de água baixo" in alertas

    r = cliente.post(f"/torres/{torre_id}/motor/ciclo",
                     json={"minutos_ligado": 10, "minutos_desligado": 50}, headers=maria)
    assert r.status_code == 200
    assert mqtt.publicados[-1][0] == f"aerotower/{torre_id}/motor/comando"

    _publicar(container, f"aerotower/{torre_id}/status", {"status": "online"})
    _publicar(container, f"aerotower/{torre_id}/info", {"firmware": "2.0.0"})
    detalhe = cliente.get(f"/torres/{torre_id}", headers=maria).json()
    assert detalhe["online"] is True and detalhe["firmware"] == "2.0.0"


def test_desvinculo_vale_na_hora(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    torre_id = _id_torre()
    _sincronizar(cliente, torre_id, "completo", dono="bia", versao=2)
    assert cliente.get(f"/torres/{torre_id}", headers=_h("bia")).status_code == 200
    _sincronizar(cliente, torre_id, "completo", dono=None, versao=3)   # torre.desvinculada
    assert cliente.get(f"/torres/{torre_id}", headers=_h("bia")).status_code == 404


def test_evento_antigo_e_ignorado(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    torre_id = _id_torre()
    _sincronizar(cliente, torre_id, dono="caio", versao=3)
    r = _sincronizar(cliente, torre_id, dono=None, versao=2)   # chegou atrasado
    assert r["aplicado"] is False
    assert cliente.get(f"/torres/{torre_id}", headers=_h("caio")).status_code == 200
    assert _sincronizar(cliente, torre_id, dono="caio", versao=3)["aplicado"] is False  # repetido


def test_kit_basico_descarta_sensores_que_nao_tem(app_e_mqtt):
    cliente, _, container = app_e_mqtt
    torre_id = _id_torre()
    _sincronizar(cliente, torre_id, "basico", dono="ana", versao=2)
    _publicar(container, f"aerotower/{torre_id}/sensores",
              {"ph": 2.1, "tds": 3, "nivelAgua": 5, "motor": True})
    r = cliente.get(f"/torres/{torre_id}/dados", headers=_h("ana")).json()
    assert r["capacidades"] == ["bomba"]
    assert r["dados"] == {"motor": True} and r["alertas"] == []


def test_topicos_estranhos_sao_ignorados(app_e_mqtt):
    _, _, container = app_e_mqtt
    for topico in ["aerotower/../sensores", "aerotower/AT-X/sensores", "outro/AT-123456/sensores",
                   "aerotower/AT-123456/coisa"]:
        _publicar(container, topico, {"ph": 6})
    assert container.estado.ultima_leitura("AT-X") is None


def test_legado_continua_funcionando(app_e_mqtt):
    cliente, mqtt, container = app_e_mqtt
    _publicar(container, "hidroponia/sensores", {"ph": 6.0, "temperatura": 25, "umidade": 60})
    r = cliente.get("/dados")
    assert r.status_code == 200 and r.json()["dados"]["ph"] == 6.0
    assert cliente.post("/motor/desligar").status_code == 200
    assert mqtt.publicados[-1][0] == "hidroponia/motor/comando"


def test_websocket_so_recebe_as_proprias_torres(app_e_mqtt):
    cliente, _, container = app_e_mqtt
    t1, t2 = _id_torre(), _id_torre()
    _sincronizar(cliente, t1, dono="lia", versao=2)
    _sincronizar(cliente, t2, dono="outro", versao=2)
    with cliente.websocket_connect(f"/ws/sensores?token={_token('lia')}") as ws:
        _publicar(container, f"aerotower/{t2}/sensores", {"ph": 6.1})
        _publicar(container, f"aerotower/{t1}/sensores", {"ph": 6.2})
        msg = ws.receive_json()
        assert msg["torreId"] == t1 and msg["dados"]["ph"] == 6.2
