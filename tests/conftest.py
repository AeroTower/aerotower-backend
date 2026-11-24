import os
import sys
import tempfile
from pathlib import Path

# Configuracao ANTES de importar o app (config.py le o ambiente no import).
_pasta = tempfile.mkdtemp()
os.environ["DATABASE_URL"]  = f"sqlite:///{_pasta}/teste.db"
os.environ["SERVICO_API_KEY"] = "servico-teste"
os.environ["ADMIN_API_KEY"]   = "admin-teste"
os.environ["JWT_SEGREDO"]     = "segredo-de-teste"
os.environ["REDIS_URL"]       = ""
os.environ["INFLUX_URL"]    = ""
os.environ["INFLUX_TOKEN"]  = ""
os.environ["INFLUX_ORG"]    = ""
os.environ["INFLUX_BUCKET"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


class _ResultadoFalso:
    rc = 0


class ClienteMqttFalso:
    """Guarda o que seria publicado, sem rede."""

    def __init__(self):
        self.publicados = []

    def publish(self, topico, payload, qos=0, retain=False):
        self.publicados.append((topico, payload))
        return _ResultadoFalso()


@pytest.fixture()
def app_e_mqtt(monkeypatch):
    import main
    from app.presentation import deps

    monkeypatch.setattr(main, "conectar", lambda cliente: True)
    monkeypatch.setattr(main, "desconectar", lambda cliente: None)
    falso = ClienteMqttFalso()
    monkeypatch.setattr(deps.container.publicador, "_cliente", falso)
    with TestClient(main.app) as cliente:
        yield cliente, falso, deps.container


class MensagemMqtt:
    def __init__(self, topico, payload: bytes):
        self.topic = topico
        self.payload = payload


# ── Tipo de cada teste, pela pasta ──────────────────────────────
# `pytest -m seguranca` roda so os de seguranca; no PyCharm, o mesmo
# filtro vai em Run Configuration > Additional Arguments.
_TIPO_POR_PASTA = {
    "unitarios":  "unitario",
    "integracao": "integracao",
    "funcionais": "funcional",
    "aceitacao":  "aceitacao",
    "desempenho": "desempenho",
    "seguranca":  "seguranca",
}


def pytest_collection_modifyitems(config, items):
    for item in items:
        tipo = _TIPO_POR_PASTA.get(Path(str(item.fspath)).parent.name)
        if tipo:
            item.add_marker(getattr(pytest.mark, tipo))
