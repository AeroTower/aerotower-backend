"""Testes da gravacao no InfluxDB (historico das leituras).

Nao precisa de um InfluxDB rodando: trocamos o write_api por um objeto falso
(MagicMock) que so anota o que recebeu, e conferimos o "line protocol" que
seria enviado ao banco.
"""
from unittest.mock import MagicMock

import pytest

from app.infrastructure.persistence import influx
from app.infrastructure.persistence.historico_influx import HistoricoInflux


@pytest.fixture
def influx_falso(monkeypatch):
    write_api = MagicMock()
    monkeypatch.setattr(influx, "client", MagicMock())
    monkeypatch.setattr(influx, "write_api", write_api)
    monkeypatch.setattr(influx, "query_api", MagicMock())
    monkeypatch.setattr(influx, "INFLUX_BUCKET", "leituras")
    return write_api


def _linha_gravada(write_api):
    """Pega o Point enviado e transforma no texto que vai para o Influx."""
    point = write_api.write.call_args.kwargs["record"]
    return point.to_line_protocol()


def test_grava_no_bucket_certo_com_tag_da_torre(influx_falso):
    influx.write_sensor_reading({"ph": 6.1}, device="AT-24DCC3A1B2C4")

    assert influx_falso.write.call_args.kwargs["bucket"] == "leituras"
    linha = _linha_gravada(influx_falso)
    assert linha.startswith("sensor_reading,device=AT-24DCC3A1B2C4 ")
    assert "ph=6.1" in linha


def test_so_campos_numericos_viram_fields(influx_falso):
    influx.write_sensor_reading(
        {"ph": 6.1, "tds": 700, "ph_status": "ok", "tanque_status": "cheio"},
        device="AT-AAAA1111",
    )

    linha = _linha_gravada(influx_falso)
    assert "ph=6.1" in linha
    assert "tds=700i" in linha          # inteiro vira "i" no line protocol
    assert "ph_status" not in linha
    assert "tanque_status" not in linha


def test_sem_configuracao_lanca_erro_claro(monkeypatch):
    monkeypatch.setattr(influx, "client", None)
    with pytest.raises(RuntimeError, match="InfluxDB não configurado"):
        influx.write_sensor_reading({"ph": 6.1})


def test_historico_sem_influx_configurado_nao_faz_nada(monkeypatch):
    monkeypatch.setattr(influx, "client", None)
    HistoricoInflux().registrar("AT-AAAA1111", {"ph": 6.1})   # nao deve lancar erro


def test_historico_engole_falha_do_influx(influx_falso):
    """Se o Influx cair, a leitura MQTT nao pode derrubar o backend."""
    influx_falso.write.side_effect = ConnectionError("influx fora do ar")
    HistoricoInflux().registrar("AT-AAAA1111", {"ph": 6.1})   # nao deve lancar erro


def test_historico_repassa_id_da_torre(influx_falso):
    HistoricoInflux().registrar("AT-BBBB2222", {"ph": 5.9})
    assert "device=AT-BBBB2222" in _linha_gravada(influx_falso)


def test_consulta_recente_usa_bucket_e_intervalo(influx_falso):
    influx.get_recent_readings(hours=6)

    query = influx.query_api.query.call_args.args[0]
    assert 'from(bucket: "leituras")' in query
    assert "range(start: -6h)" in query
    assert 'r._measurement == "sensor_reading"' in query


@pytest.mark.parametrize("invalido", [0, -1, "1); drop()", 1.5, True])
def test_consulta_recusa_intervalo_invalido(influx_falso, invalido):
    """Refatoracao: so inteiro positivo entra no texto da query."""
    with pytest.raises(ValueError):
        influx.get_recent_readings(hours=invalido)
    influx.query_api.query.assert_not_called()


def test_montar_ponto_sem_gravar():
    linha = influx.montar_ponto({"ph": 6.0, "status": "ok"}, device="AT-AAAA1111").to_line_protocol()
    assert linha.startswith("sensor_reading,device=AT-AAAA1111 ph=6")
    assert "status" not in linha
