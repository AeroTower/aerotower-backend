"""Testes de seguranca: tentativas de ataque e de acesso indevido.

Cada teste simula o que um atacante faria e confere que o Backend recusa
sem vazar informacao.
"""
import base64
import json

import pytest
from starlette.websockets import WebSocketDisconnect

from app.presentation import deps
from tests.apoio import SERVICO, cabecalho, id_torre, publicar, token, torre_de


def _sem_assinatura(dados):
    """JWT com alg "none": o truque classico para pular a assinatura."""
    def parte(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    return f"{parte({'alg': 'none', 'typ': 'JWT'})}.{parte(dados)}."


def test_token_sem_assinatura_e_recusado(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    falso = _sem_assinatura({"sub": "maria", "iss": "aerotower-auth", "aud": "aerotower",
                             "exp": 9999999999})
    r = cliente.get("/torres", headers={"Authorization": f"Bearer {falso}"})
    assert r.status_code == 401 and r.headers["WWW-Authenticate"] == "Bearer"


def test_token_de_outro_app_e_recusado(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    outro_app = token("maria", aud="outro-sistema")
    assert cliente.get("/torres", headers={"Authorization": f"Bearer {outro_app}"}).status_code == 401


def test_token_sem_usuario_e_recusado(app_e_mqtt):
    import jwt
    cliente, _, _ = app_e_mqtt
    sem_sub = jwt.encode({"iss": "aerotower-auth", "aud": "aerotower", "exp": 9999999999},
                         "segredo-de-teste", algorithm="HS256")
    assert cliente.get("/torres", headers={"Authorization": f"Bearer {sem_sub}"}).status_code == 401


@pytest.mark.parametrize("metodo, sufixo", [
    ("get", ""), ("get", "/dados"), ("get", "/alertas"), ("get", "/thresholds"),
    ("post", "/thresholds"), ("post", "/motor/desligar"), ("get", "/motor/status"),
    ("get", "/plantas"),
])
def test_torre_de_outra_pessoa_responde_404_e_nao_403(app_e_mqtt, metodo, sufixo):
    """403 contaria ao curioso que aquele id existe."""
    cliente, mqtt, _ = app_e_mqtt
    torre, _ = torre_de(cliente, "dona")
    kwargs = {"json": {}} if metodo == "post" else {}
    r = getattr(cliente, metodo)(f"/torres/{torre}{sufixo}", headers=cabecalho("intruso"), **kwargs)
    assert r.status_code == 404
    assert mqtt.publicados == []


def test_rota_interna_fica_desligada_sem_chave_configurada(app_e_mqtt, monkeypatch):
    cliente, _, _ = app_e_mqtt
    monkeypatch.setattr(deps, "SERVICO_API_KEY", "")
    r = cliente.put(f"/internal/torres/{id_torre()}", headers=SERVICO,
                    json={"kit": "pro", "donoId": "hacker", "versao": 1})
    assert r.status_code == 403


def test_id_de_torre_malicioso_na_rota_interna(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    r = cliente.put("/internal/torres/AT-1'%20OR%20'1'='1", headers=SERVICO,
                    json={"kit": "pro", "donoId": "x", "versao": 1})
    assert r.status_code == 422


def test_websocket_com_token_invalido_e_fechado(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    with pytest.raises(WebSocketDisconnect) as erro, cliente.websocket_connect("/ws/sensores?token=falso") as ws:
        ws.receive_json()
    assert erro.value.code == 1008


def test_websocket_nao_entrega_torre_alheia_mesmo_pedindo(app_e_mqtt, monkeypatch):
    cliente, _, container = app_e_mqtt
    alheia, _ = torre_de(cliente, "vitima")
    torre_de(cliente, "atacante")
    registrados = []
    original = container.notificador.registrar
    monkeypatch.setattr(container.notificador, "registrar",
                        lambda ws, torres: (registrados.append(set(torres)), original(ws, torres)))
    with cliente.websocket_connect(f"/ws/sensores?token={token('atacante')}&torre={alheia}"):
        pass
    assert registrados == [set()]     # pediu a torre da vitima e ficou sem nenhuma


def test_nome_de_planta_com_sql_e_guardado_como_texto(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    torre, h = torre_de(cliente, "ana")
    nome = "x'); DROP TABLE plantas; --"
    assert cliente.post(f"/torres/{torre}/plantas", headers=h,
                        data={"nome": nome, "tipo": "erva", "data_plantio": "2026-11-21"}).status_code == 201
    assert [p["nome"] for p in cliente.get(f"/torres/{torre}/plantas", headers=h).json()] == [nome]


@pytest.mark.parametrize("arquivo", ["foto.jpg.php", "foto.svg", "foto", "../../main.py"])
def test_upload_so_aceita_imagem(app_e_mqtt, arquivo):
    cliente, _, _ = app_e_mqtt
    torre, h = torre_de(cliente, "ana")
    r = cliente.post(f"/torres/{torre}/plantas", headers=h,
                     data={"nome": "X", "tipo": "erva", "data_plantio": "2026-11-21"},
                     files={"foto": (arquivo, b"conteudo", "application/octet-stream")})
    assert r.status_code == 400


def test_topico_forjado_nao_cria_torre(app_e_mqtt):
    _, _, container = app_e_mqtt
    for topico in ["aerotower/+/sensores", "aerotower/#/sensores", "aerotower/AT-X';--/sensores"]:
        publicar(container, topico, {"ph": 1})
    assert all(not k.startswith("AT-X") for k in container.estado._leituras)


def test_campos_gigantes_na_loja_sao_recusados(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    r = cliente.post("/eventos", json={"nome": "cta_diy", "pagina": "/", "sessao": "s" * 10_000})
    assert r.status_code == 422
