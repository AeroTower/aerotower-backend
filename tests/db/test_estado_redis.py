"""Testes do estado em Redis (ultima leitura, motor e thresholds por torre).

Usa Redis real se TEST_REDIS_URL estiver definida; senao, fakeredis.
"""
from datetime import datetime

import fakeredis
import pytest
import redis

from app.domain.entities.leitura import LeituraAvaliada, LeituraSensores, StatusMotor
from app.infrastructure.state.estado_redis import EstadoRedis

TORRE = "AT-24DCC3A1B2C4"
OUTRA = "AT-AAAA1111"


@pytest.fixture
def conexao(redis_url, monkeypatch):
    """Devolve uma funcao que cria um EstadoRedis novo (simula restart)
    apontando sempre para o mesmo Redis."""
    if redis_url:
        cliente = redis.from_url(redis_url, decode_responses=True)
        cliente.flushdb()
        url = redis_url
    else:
        servidor = fakeredis.FakeServer()
        cliente = fakeredis.FakeRedis(server=servidor, decode_responses=True)
        # EstadoRedis chama redis.from_url(...): trocamos por um fake.
        monkeypatch.setattr(
            "app.infrastructure.state.estado_redis.redis.from_url",
            lambda *_a, **_k: fakeredis.FakeRedis(server=servidor, decode_responses=True),
        )
        url = "redis://fake"
    yield (lambda: EstadoRedis(url)), cliente
    cliente.flushdb()


def _leitura(ph=6.1):
    return LeituraAvaliada(
        leitura=LeituraSensores(bruto={"ph": ph, "tds": 700}, recebido_em=datetime(2026, 11, 20, 10, 30)),
        alertas=["ph_alto"] if ph > 6.5 else [],
    )


def test_sem_dado_devolve_none(conexao):
    novo, _ = conexao
    estado = novo()
    assert estado.ultima_leitura(TORRE) is None
    assert estado.ultimo_status_motor(TORRE) is None


def test_leitura_ida_e_volta_preserva_dados_e_data(conexao):
    novo, _ = conexao
    estado = novo()
    estado.salvar_leitura(TORRE, _leitura(ph=7.0))

    lida = estado.ultima_leitura(TORRE)

    assert lida.leitura.bruto == {"ph": 7.0, "tds": 700}
    assert lida.leitura.recebido_em == datetime(2026, 11, 20, 10, 30)
    assert lida.alertas == ["ph_alto"]


def test_leitura_sobrevive_a_restart(conexao):
    """O motivo de usar Redis: reiniciar o backend nao perde o estado."""
    novo, _ = conexao
    novo().salvar_leitura(TORRE, _leitura())

    depois_do_restart = novo()

    assert depois_do_restart.ultima_leitura(TORRE) is not None


def test_cada_torre_tem_sua_chave(conexao):
    novo, cliente = conexao
    estado = novo()
    estado.salvar_leitura(TORRE, _leitura(ph=6.0))
    estado.salvar_leitura(OUTRA, _leitura(ph=5.0))

    assert estado.ultima_leitura(TORRE).leitura.bruto["ph"] == 6.0
    assert estado.ultima_leitura(OUTRA).leitura.bruto["ph"] == 5.0
    assert cliente.exists(f"aerotower:{TORRE}:leitura")
    assert cliente.exists(f"aerotower:{OUTRA}:leitura")


def test_nova_leitura_substitui_a_anterior(conexao):
    novo, _ = conexao
    estado = novo()
    estado.salvar_leitura(TORRE, _leitura(ph=6.0))
    estado.salvar_leitura(TORRE, _leitura(ph=6.3))
    assert estado.ultima_leitura(TORRE).leitura.bruto["ph"] == 6.3


def test_status_motor_ida_e_volta(conexao):
    novo, _ = conexao
    estado = novo()
    estado.salvar_status_motor(TORRE, StatusMotor(bruto={"motor": "ligado"}, recebido_em=None))

    status = estado.ultimo_status_motor(TORRE)

    assert status.bruto == {"motor": "ligado"}
    assert status.recebido_em is None


def test_thresholds_padrao_quando_nada_foi_salvo(conexao):
    novo, _ = conexao
    t = novo().thresholds(TORRE)
    assert (t.ph_min, t.ph_max) == (5.5, 6.5)


def test_thresholds_salvos_sobrevivem_a_restart(conexao):
    novo, _ = conexao
    estado = novo()
    t = estado.thresholds(TORRE)
    t.aplicar({"phMin": 5.8, "phMax": 6.2})
    estado.salvar_thresholds(TORRE, t)

    recarregado = novo().thresholds(TORRE)

    assert (recarregado.ph_min, recarregado.ph_max) == (5.8, 6.2)
    assert recarregado.ec_max == 1.8   # campo nao alterado continua no padrao


def test_redis_fora_do_ar_falha_na_criacao():
    """Sem Redis, o EstadoRedis ja falha no __init__ (ping), em vez de
    quebrar so na primeira leitura do sensor."""
    with pytest.raises(redis.exceptions.ConnectionError):
        EstadoRedis("redis://localhost:1")   # porta sem servidor


def test_salvar_thresholds_novos_atualiza_o_cache(conexao):
    """Refatoracao: antes, salvar um objeto Thresholds novo gravava no Redis
    mas os alertas continuavam usando o antigo (cache) ate o restart."""
    from app.domain.entities.thresholds import Thresholds
    novo, _ = conexao
    estado = novo()
    estado.thresholds(TORRE)                 # carrega o padrao no cache

    estado.salvar_thresholds(TORRE, Thresholds(ph_min=5.0, ph_max=7.0))

    assert estado.thresholds(TORRE).ph_max == 7.0
