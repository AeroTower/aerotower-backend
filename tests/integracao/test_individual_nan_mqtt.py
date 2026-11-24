"""CT-INT-02 (teste individual) — Leitura com NaN/Infinity pelo MQTT.

Interface testada: broker MQTT -> assinante do Backend -> caso de uso
ProcessarLeitura -> estado -> rotas HTTP do painel.

Cenario: uma torre (sensor com defeito, firmware alterado ou alguem com a
credencial do broker, que hoje e a mesma para todas as torres) publica
{"ph": NaN} ou {"ph": 1e999}. O json do Python aceita os dois.
Esperado: o Backend descarta o valor invalido; o painel continua abrindo
(HTTP 200) e nao mostra "inf" num alerta.
Obtido hoje: com NaN, GET /torres/{id}/dados responde 500 (o FastAPI nao
consegue transformar NaN em JSON) e o painel do dono para de abrir ate a
torre mandar outra leitura. Com Infinity, o alerta diz
"pH acima do limite: inf".
"""
import pytest
from fastapi.testclient import TestClient

from tests.apoio import publicar, torre_de

pytestmark = pytest.mark.defeito


def _como_em_producao(app):
    # Erro do servidor vira HTTP 500, como no uvicorn da Azure (o TestClient
    # padrao relancaria a excecao dentro do teste).
    return TestClient(app, raise_server_exceptions=False)


def test_leitura_com_nan_nao_derruba_o_painel(app_e_mqtt):
    cliente, _, container = app_e_mqtt
    torre, dono = torre_de(cliente, "dona-nan")

    publicar(container, f"aerotower/{torre}/sensores", b'{"ph": NaN, "nivelAgua": 80}')

    r = _como_em_producao(cliente.app).get(f"/torres/{torre}/dados", headers=dono)
    assert r.status_code == 200, f"painel quebrou: HTTP {r.status_code} {r.text[:80]}"
    assert r.json()["dados"].get("ph") is None


def test_leitura_com_infinito_nao_vira_alerta(app_e_mqtt):
    cliente, _, container = app_e_mqtt
    torre, dono = torre_de(cliente, "dona-inf")

    publicar(container, f"aerotower/{torre}/sensores", b'{"ph": 1e999, "nivelAgua": 80}')

    alertas = cliente.get(f"/torres/{torre}/alertas", headers=dono).json()["alertas"]
    assert not any("inf" in a for a in alertas), f"alerta com valor infinito: {alertas}"
    r = _como_em_producao(cliente.app).get(f"/torres/{torre}/dados", headers=dono)
    assert r.status_code == 200, f"painel quebrou: HTTP {r.status_code}"
