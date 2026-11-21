"""Testes de desempenho: carga, volume e escalabilidade.

Os limites de tempo sao folgados de proposito (cerca de 10x o medido no
GitHub Actions), para o teste falhar so quando algo ficar muito mais
lento, e nao por oscilacao da maquina.
"""
import time

from app.infrastructure.persistence import catalogo_torres
from tests.apoio import id_torre, publicar, sincronizar, torre_de

MENSAGENS = 2_000


def test_carga_mqtt_100_torres_publicando(app_e_mqtt):
    """Teste de carga: 100 torres x 20 leituras chegando pelo MQTT."""
    cliente, _, container = app_e_mqtt
    torres = [id_torre() for _ in range(100)]
    for t in torres:
        sincronizar(cliente, t, kit="pro", dono="carga", versao=2)

    inicio = time.perf_counter()
    for i in range(MENSAGENS):
        publicar(container, f"aerotower/{torres[i % 100]}/sensores", {"ph": 6.0, "nivelAgua": 50})
    duracao = time.perf_counter() - inicio

    assert duracao < 10, f"{MENSAGENS} mensagens levaram {duracao:.2f}s"
    assert all(container.estado.ultima_leitura(t) is not None for t in torres)


def test_cache_do_catalogo_evita_consulta_por_mensagem(app_e_mqtt, monkeypatch):
    """Escalabilidade: com 20 msg/s por torre, o kit nao pode ir ao banco toda vez."""
    cliente, _, container = app_e_mqtt
    torre, _ = torre_de(cliente, "cache")
    container.catalogo.esquecer(torre)

    consultas = []
    original = catalogo_torres.SessionLocal

    def contando():
        consultas.append(1)
        return original()

    monkeypatch.setattr(catalogo_torres, "SessionLocal", contando)
    for _ in range(500):
        publicar(container, f"aerotower/{torre}/sensores", {"ph": 6.0})
    assert len(consultas) == 1


def test_cache_do_catalogo_expira():
    catalogo = catalogo_torres.CatalogoSqlAlchemy(validade_s=0)
    assert catalogo.capacidades("AT-NAOEXISTE1") is None
    assert catalogo.capacidades("AT-NAOEXISTE1") is None   # consultou de novo, sem erro


def test_tempo_de_resposta_da_listagem_de_torres(app_e_mqtt):
    """Volume: dono com 50 torres; 100 listagens seguidas."""
    cliente, _, _ = app_e_mqtt
    for _ in range(49):
        torre_de(cliente, "volume")
    _, h = torre_de(cliente, "volume")

    inicio = time.perf_counter()
    for _ in range(100):
        r = cliente.get("/torres", headers=h)
    media_ms = (time.perf_counter() - inicio) * 10

    assert r.status_code == 200 and len(r.json()) == 50
    assert media_ms < 200, f"média de {media_ms:.1f} ms por requisição"


def test_pico_de_eventos_da_loja(app_e_mqtt):
    """Teste de spike: 300 cliques de CTA de uma vez."""
    cliente, _, _ = app_e_mqtt
    inicio = time.perf_counter()
    respostas = [cliente.post("/eventos", json={"nome": "cta_add_carrinho", "pagina": "/loja",
                                                "sessao": f"s{i}"}) for i in range(300)]
    duracao = time.perf_counter() - inicio
    assert {r.status_code for r in respostas} == {201}
    assert duracao < 15
