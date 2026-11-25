"""Testes de integracao: rotas HTTP + banco SQLite + MQTT falso.

Conferem a interface entre as camadas (apresentacao -> caso de uso ->
repositorio/MQTT), com o app FastAPI de verdade e so o broker trocado por
um duble.
"""
import json

from app.domain.exceptions import FalhaNaPublicacao
from tests.apoio import ADMIN, publicar, torre_de, torre_legada_de


# ── Rotas gerais e CORS ──────────────────────────────────────

def test_home_mostra_o_formato_dos_topicos(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    assert cliente.get("/").json()["mqttTopic"] == "aerotower/<torre_id>/sensores"


def test_preflight_cors_e_cabecalho_nas_respostas(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    r = cliente.options("/torres")
    assert r.status_code == 200 and r.headers["Access-Control-Allow-Methods"] == "*"
    assert cliente.get("/").headers["Access-Control-Allow-Origin"] == "*"


# ── Validacao da loja (/eventos) ─────────────────────────────

def test_eventos_resumo_interesses_e_exportacao(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    for sessao in ["s1", "s1", "s2"]:
        assert cliente.post("/eventos", json={"nome": "cta_ver_kits", "pagina": "/loja",
                                              "sessao": sessao}).status_code == 201
    r = cliente.post("/eventos/interesse", json={"email": "Ana@Exemplo.com", "produto": "pro",
                                                 "sessao": "s1"})
    assert r.status_code == 201

    resumo = cliente.get("/eventos/resumo").json()
    kits = next(e for e in resumo["eventos"] if e["nome"] == "cta_ver_kits")
    assert kits["total"] >= 3 and kits["sessoes"] >= 2
    assert resumo["total_interesses"] >= 1

    assert "ana@exemplo.com" in [i["email"] for i in cliente.get("/eventos/interesses", headers=ADMIN).json()]
    assert any(e["sessao"] == "s2" for e in cliente.get("/eventos/exportar", headers=ADMIN).json())

    csv = cliente.get("/eventos/exportar.csv", headers=ADMIN)
    assert csv.headers["content-type"].startswith("text/csv")
    assert csv.text.splitlines()[0] == "id,evento,pagina,sessao,criado_em"
    assert "cta_ver_kits" in csv.text


def test_evento_e_email_invalidos_dao_422(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    assert cliente.post("/eventos", json={"nome": "inventado", "sessao": "s"}).status_code == 422
    assert cliente.post("/eventos/interesse", json={"email": "sem-arroba", "produto": "pro",
                                                    "sessao": "s"}).status_code == 422


# ── Thresholds, alertas e motor por torre ────────────────────

def test_thresholds_por_torre_mudam_os_alertas(app_e_mqtt):
    cliente, _, container = app_e_mqtt
    torre, h = torre_de(cliente, "lucas")
    assert cliente.get(f"/torres/{torre}/thresholds", headers=h).json()["phMax"] == 6.5

    r = cliente.post(f"/torres/{torre}/thresholds", headers=h, json={"phMax": 8.0})
    assert r.status_code == 200 and r.json()["thresholds"]["phMax"] == 8.0

    publicar(container, f"aerotower/{torre}/sensores", {"ph": 7.5})
    assert cliente.get(f"/torres/{torre}/alertas", headers=h).json() == {"alertas": []}


def test_torre_sem_leitura_ou_status_responde_503(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    torre, h = torre_de(cliente, "nina")
    assert cliente.get(f"/torres/{torre}/dados", headers=h).status_code == 503
    assert cliente.get(f"/torres/{torre}/motor/status", headers=h).status_code == 503


def test_desligar_e_status_do_motor(app_e_mqtt):
    cliente, mqtt, container = app_e_mqtt
    torre, h = torre_de(cliente, "rui")
    r = cliente.post(f"/torres/{torre}/motor/desligar", headers=h)
    assert r.status_code == 200 and r.json()["comando"] == {"acao": "desligar"}
    assert mqtt.publicados[-1] == (f"aerotower/{torre}/motor/comando", json.dumps({"acao": "desligar"}))

    publicar(container, f"aerotower/{torre}/motor/status", {"ligado": False, "ciclo_ativo": False})
    status = cliente.get(f"/torres/{torre}/motor/status", headers=h).json()
    assert status["ligado"] is False and "recebidoEm" in status


def test_broker_recusando_comando_responde_502(app_e_mqtt, monkeypatch):
    cliente, _, container = app_e_mqtt
    torre, h = torre_de(cliente, "eva")

    def recusa(*a, **k):
        raise FalhaNaPublicacao(4)

    monkeypatch.setattr(container.publicador, "publicar", recusa)
    assert cliente.post(f"/torres/{torre}/motor/desligar", headers=h).status_code == 502


def test_ciclo_fora_da_faixa_e_recusado(app_e_mqtt):
    cliente, mqtt, _ = app_e_mqtt
    torre, h = torre_de(cliente, "téo")
    r = cliente.post(f"/torres/{torre}/motor/ciclo", headers=h,
                     json={"minutos_ligado": 0, "minutos_desligado": 5000})
    assert r.status_code == 422 and mqtt.publicados == []


# ── Plantas com foto ─────────────────────────────────────────

def test_planta_com_foto_e_busca_por_id(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    torre, h = torre_de(cliente, "gabi")
    r = cliente.post(f"/torres/{torre}/plantas", headers=h,
                     data={"nome": "Hortelã", "tipo": "erva", "data_plantio": "2026-11-21"},
                     files={"foto": ("hortela.jpg", b"\xff\xd8\xff", "image/jpeg")})
    assert r.status_code == 201, r.text
    planta = r.json()
    assert planta["foto_url"].startswith("/static/fotos/") and planta["foto_url"].endswith(".jpg")

    achada = cliente.get(f"/torres/{torre}/plantas/{planta['id']}", headers=h)
    assert achada.status_code == 200 and achada.json()["nome"] == "Hortelã"
    assert cliente.get(f"/torres/{torre}/plantas/999999", headers=h).status_code == 404
    assert cliente.delete(f"/torres/{torre}/plantas/{planta['id']}", headers=h).status_code == 200


def test_foto_em_formato_nao_aceito_da_400(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    torre, h = torre_de(cliente, "gabi")
    r = cliente.post(f"/torres/{torre}/plantas", headers=h,
                     data={"nome": "X", "tipo": "erva", "data_plantio": "2026-11-21"},
                     files={"foto": ("script.html", b"<script>", "text/html")})
    assert r.status_code == 400


# ── Rotas legadas (torre do prototipo) ───────────────────────

def test_legado_thresholds_alertas_e_motor(app_e_mqtt):
    cliente, mqtt, container = app_e_mqtt
    dono = torre_legada_de(cliente, "dono-do-prototipo")
    r = cliente.post("/thresholds", json={"nivelAguaMin": 50}, headers=dono)
    assert r.json()["thresholds"]["nivelAguaMin"] == 50
    assert cliente.get("/thresholds").json()["nivelAguaMin"] == 50

    publicar(container, "hidroponia/sensores", {"nivelAgua": 40})
    assert any("Nível" in a for a in cliente.get("/alertas").json()["alertas"])

    r = cliente.post("/motor/ciclo", json={"minutos_ligado": 5, "minutos_desligado": 25}, headers=dono)
    assert r.status_code == 200 and mqtt.publicados[-1][0] == "hidroponia/motor/comando"

    publicar(container, "hidroponia/motor/status", {"ligado": True})
    assert cliente.get("/motor/status").json()["ligado"] is True


# ── WebSocket ────────────────────────────────────────────────

def test_websocket_sem_token_acompanha_a_torre_legada(app_e_mqtt):
    cliente, _, container = app_e_mqtt
    with cliente.websocket_connect("/ws/sensores") as ws:
        publicar(container, "hidroponia/sensores", {"ph": 6.3})
        assert ws.receive_json()["torreId"] == "AT-LEGADO"


def test_websocket_filtrado_por_uma_torre(app_e_mqtt):
    from tests.apoio import token
    cliente, _, container = app_e_mqtt
    t1, _ = torre_de(cliente, "zeca")
    t2, _ = torre_de(cliente, "zeca")
    with cliente.websocket_connect(f"/ws/sensores?token={token('zeca')}&torre={t2.lower()}") as ws:
        publicar(container, f"aerotower/{t1}/sensores", {"ph": 6.0})
        publicar(container, f"aerotower/{t2}/sensores", {"ph": 6.4})
        assert ws.receive_json()["torreId"] == t2


# ── Repositorio de eventos direto no banco ───────────────────

def test_repositorio_de_eventos_ordena_resumo_por_total(tmp_path):
    from datetime import datetime

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.domain.entities.evento import Evento
    from app.infrastructure.persistence.database import Base
    from app.infrastructure.persistence.sqlalchemy_evento_repository import SqlAlchemyEventoRepository

    engine = create_engine(f"sqlite:///{tmp_path}/eventos.db")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as sessao:
        repo = SqlAlchemyEventoRepository(sessao)
        for nome, s in [("cta_diy", "a"), ("cta_ver_kits", "a"), ("cta_ver_kits", "b")]:
            repo.registrar_evento(Evento(nome=nome, pagina="/", sessao=s, criado_em=datetime.now()))
        resumo = repo.resumo()
    assert [c.nome for c in resumo.eventos] == ["cta_ver_kits", "cta_diy"]
    assert resumo.total_sessoes == 2 and resumo.total_interesses == 0
