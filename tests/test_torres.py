import json
import uuid

from tests.conftest import MensagemMqtt

ADMIN = {"X-Admin-Key": "chave-de-teste"}


def _id_torre():
    return "AT-" + uuid.uuid4().hex[:12].upper()


def _login(cliente, nome):
    r = cliente.post("/auth/dev", json={"id": nome})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _cadastrar(cliente, kit="pro"):
    torre_id = _id_torre()
    r = cliente.post("/admin/torres", json={"torreId": torre_id, "kit": kit}, headers=ADMIN)
    assert r.status_code == 201, r.text
    return torre_id, r.json()["codigoAtivacao"]


def _publicar(container, topico, dados):
    container.subscriber._on_message(None, None, MensagemMqtt(topico, json.dumps(dados).encode()))


def test_admin_exige_chave(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    r = cliente.post("/admin/torres", json={"torreId": _id_torre(), "kit": "pro"})
    assert r.status_code == 403
    r = cliente.post("/admin/torres", json={"torreId": _id_torre(), "kit": "pro"},
                     headers={"X-Admin-Key": "errada"})
    assert r.status_code == 403


def test_id_invalido_recusado(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    r = cliente.post("/admin/torres", json={"torreId": "../#", "kit": "pro"}, headers=ADMIN)
    assert r.status_code == 422


def test_rotas_de_torre_exigem_login(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    assert cliente.get("/torres").status_code == 401
    assert cliente.get("/torres", headers={"Authorization": "Bearer lixo"}).status_code == 401


def test_fluxo_completo_e_isolamento(app_e_mqtt):
    cliente, mqtt, container = app_e_mqtt
    torre_id, codigo = _cadastrar(cliente, "pro")
    maria = _login(cliente, "maria")
    joao = _login(cliente, "joao")

    # Maria ativa digitando o código de qualquer jeito (minúsculo, sem hífen)
    r = cliente.post("/torres/ativar", json={"codigo": codigo.lower().replace("-", ""),
                                             "apelido": "Varanda"}, headers=maria)
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["id"] == torre_id
    assert corpo["capacidades"] == ["bomba", "nivel", "ph", "tds", "clima"]

    # Código queimado: nem Maria nem João usam de novo
    assert cliente.post("/torres/ativar", json={"codigo": codigo}, headers=joao).status_code == 400

    # Listagem separada por dono
    assert [t["id"] for t in cliente.get("/torres", headers=maria).json()] == [torre_id]
    assert cliente.get("/torres", headers=joao).json() == []

    # João não enxerga nem comanda a torre da Maria (404, não 403)
    assert cliente.get(f"/torres/{torre_id}/dados", headers=joao).status_code == 404
    assert cliente.post(f"/torres/{torre_id}/motor/desligar", headers=joao).status_code == 404
    assert mqtt.publicados == []

    # Leitura chega pelo tópico da torre
    _publicar(container, f"aerotower/{torre_id}/sensores",
              {"ph": 7.4, "tds": 600, "temperaturaAmbiente": 24.1, "nivelAgua": 20.0})
    r = cliente.get(f"/torres/{torre_id}/dados", headers=maria)
    assert r.status_code == 200
    alertas = " ".join(r.json()["alertas"])
    assert "pH acima" in alertas and "Nível de água baixo" in alertas

    # Comando vai para a caixa desta torre
    r = cliente.post(f"/torres/{torre_id}/motor/ciclo",
                     json={"minutos_ligado": 10, "minutos_desligado": 50}, headers=maria)
    assert r.status_code == 200
    assert mqtt.publicados[-1][0] == f"aerotower/{torre_id}/motor/comando"

    # Status e presença
    _publicar(container, f"aerotower/{torre_id}/status", {"status": "online"})
    _publicar(container, f"aerotower/{torre_id}/info", {"firmware": "2.0.0", "kit": "pro"})
    detalhe = cliente.get(f"/torres/{torre_id}", headers=maria).json()
    assert detalhe["online"] is True and detalhe["firmware"] == "2.0.0"


def test_kit_basico_descarta_sensores_que_nao_tem(app_e_mqtt):
    cliente, _, container = app_e_mqtt
    torre_id, codigo = _cadastrar(cliente, "basico")
    ana = _login(cliente, "ana")
    cliente.post("/torres/ativar", json={"codigo": codigo}, headers=ana)

    # Pino de pH solto lendo ruído numa torre básica
    _publicar(container, f"aerotower/{torre_id}/sensores",
              {"ph": 2.1, "tds": 3, "nivelAgua": 5, "motor": True})
    r = cliente.get(f"/torres/{torre_id}/dados", headers=ana).json()
    assert r["capacidades"] == ["bomba"]
    assert r["dados"] == {"motor": True}
    assert r["alertas"] == []


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


def test_novo_codigo_desvincula(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    torre_id, codigo = _cadastrar(cliente, "completo")
    bia = _login(cliente, "bia")
    cliente.post("/torres/ativar", json={"codigo": codigo}, headers=bia)

    r = cliente.post(f"/admin/torres/{torre_id}/novo-codigo", headers=ADMIN)
    novo = r.json()["codigoAtivacao"]
    assert novo != codigo
    assert cliente.get("/torres", headers=bia).json() == []

    caio = _login(cliente, "caio")
    r = cliente.post("/torres/ativar", json={"codigo": novo}, headers=caio)
    assert r.status_code == 201 and r.json()["capacidades"] == ["bomba", "nivel"]


def test_websocket_so_recebe_as_proprias_torres(app_e_mqtt):
    cliente, _, container = app_e_mqtt
    t1, c1 = _cadastrar(cliente)
    t2, c2 = _cadastrar(cliente)
    r = cliente.post("/auth/dev", json={"id": "lia"})
    token = r.json()["token"]
    lia = {"Authorization": f"Bearer {token}"}
    cliente.post("/torres/ativar", json={"codigo": c1}, headers=lia)
    outro = _login(cliente, "outro")
    cliente.post("/torres/ativar", json={"codigo": c2}, headers=outro)

    with cliente.websocket_connect(f"/ws/sensores?token={token}") as ws:
        _publicar(container, f"aerotower/{t2}/sensores", {"ph": 6.1})   # de outra pessoa
        _publicar(container, f"aerotower/{t1}/sensores", {"ph": 6.2})   # da Lia
        msg = ws.receive_json()
        assert msg["torreId"] == t1 and msg["dados"]["ph"] == 6.2


def test_google_recusa_token_falso(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    assert cliente.post("/auth/google", json={"idToken": "falso"}).status_code == 401


def test_google_aceita_so_o_nosso_client_id(app_e_mqtt, monkeypatch):
    from google.oauth2 import id_token
    cliente, _, _ = app_e_mqtt

    def falso(aud):
        return lambda token, req: {"iss": "https://accounts.google.com", "aud": aud,
                                   "sub": "1098765", "email": "m@x.com", "email_verified": True,
                                   "name": "Maria"}

    monkeypatch.setattr(id_token, "verify_oauth2_token", falso("outro-app.apps.googleusercontent.com"))
    assert cliente.post("/auth/google", json={"idToken": "x"}).status_code == 401

    monkeypatch.setattr(id_token, "verify_oauth2_token", falso("cliente-teste.apps.googleusercontent.com"))
    r = cliente.post("/auth/google", json={"idToken": "x"})
    assert r.status_code == 200
    assert r.json()["usuario"] == {"id": "1098765", "email": "m@x.com", "nome": "Maria"}
    me = cliente.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['token']}"})
    assert me.json()["id"] == "1098765"
