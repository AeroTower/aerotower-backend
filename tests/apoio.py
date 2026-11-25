"""Funcoes de apoio usadas pelos testes de integracao, seguranca e desempenho."""
import itertools
import json
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from tests.conftest import MensagemMqtt

SERVICO = {"X-Service-Key": "servico-teste"}
ADMIN = {"X-Admin-Key": "admin-teste"}
_versoes = itertools.count(1000)


def token(usuario_id, segredo="segredo-de-teste", emissor="aerotower-auth", minutos=60, **extra):
    """Token igual ao que o auth-aerotower emite."""
    agora = datetime.now(timezone.utc)
    dados = {"sub": usuario_id, "iss": emissor, "aud": "aerotower",
             "iat": agora, "exp": agora + timedelta(minutes=minutos), **extra}
    return jwt.encode(dados, segredo, algorithm="HS256")


def cabecalho(usuario_id, **kw):
    return {"Authorization": f"Bearer {token(usuario_id, **kw)}"}


def id_torre():
    return "AT-" + uuid.uuid4().hex[:12].upper()


def sincronizar(cliente, torre_id, kit="pro", dono=None, versao=1, apelido=None):
    r = cliente.put(f"/internal/torres/{torre_id}", headers=SERVICO,
                    json={"kit": kit, "donoId": dono, "apelido": apelido, "versao": versao})
    assert r.status_code == 200, r.text
    return r.json()


def torre_de(cliente, dono, kit="pro"):
    """Cria uma torre ja vinculada a `dono` e devolve (id, cabecalho do dono)."""
    torre_id = id_torre()
    sincronizar(cliente, torre_id, kit=kit, dono=dono, versao=2)
    return torre_id, cabecalho(dono)


def torre_legada_de(cliente, dono):
    """Vincula a TORRE_LEGADA (prototipo) a `dono` e devolve o cabecalho dele."""
    from app.core.config import TORRE_LEGADA
    sincronizar(cliente, TORRE_LEGADA, dono=dono, versao=next(_versoes))
    return cabecalho(dono)


def publicar(container, topico, dados):
    corpo = dados if isinstance(dados, bytes) else json.dumps(dados).encode()
    container.subscriber._on_message(None, None, MensagemMqtt(topico, corpo))
