from typing import Any, Dict

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# As variaveis vem do config.py, que ja carrega o .env. (Antes este arquivo
# lia um "env.env" por conta propria, mas o caminho apontava para a pasta
# ACIMA do repositorio, entao esse arquivo nunca era encontrado.)
from app.core.config import INFLUX_BUCKET, INFLUX_ORG, INFLUX_TOKEN, INFLUX_URL

MEDICAO = "sensor_reading"

if INFLUX_URL and INFLUX_TOKEN and INFLUX_ORG and INFLUX_BUCKET:
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    query_api = client.query_api()
else:
    client = None
    write_api = None
    query_api = None


def _validar_influx():
    if client is None or write_api is None or query_api is None:
        raise RuntimeError(
            "InfluxDB não configurado. Defina INFLUX_URL, INFLUX_TOKEN, "
            "INFLUX_ORG e INFLUX_BUCKET no .env (ou nas Application Settings da Azure)."
        )


def campos_numericos(dados: Dict[str, Any]) -> Dict[str, Any]:
    """So numeros viram field no Influx; textos como "ph_status" ficam de fora.

    Atencao: em Python, True/False tambem sao int, entao booleanos
    (ex.: "ciclo_ativo") entram — e o Influx grava como boolean.
    """
    return {campo: valor for campo, valor in dados.items() if isinstance(valor, (int, float))}


def montar_ponto(dados: Dict[str, Any], device: str) -> Point:
    """Monta o Point sem gravar. Separado para poder testar sem banco."""
    point = Point(MEDICAO).tag("device", device)
    for campo, valor in campos_numericos(dados).items():
        point = point.field(campo, valor)
    return point


def write_sensor_reading(dados: dict, device: str = "hidroponia_01"):
    """Grava uma leitura de sensores no InfluxDB."""
    _validar_influx()
    write_api.write(bucket=INFLUX_BUCKET, record=montar_ponto(dados, device))


def get_recent_readings(hours: int = 1):
    _validar_influx()
    # A query e montada com f-string: garante que `hours` e um inteiro
    # positivo, para nada alem de um numero entrar no texto da consulta.
    if isinstance(hours, bool) or not isinstance(hours, int) or hours <= 0:
        raise ValueError(f"hours deve ser um inteiro positivo, recebido: {hours!r}")
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r._measurement == "{MEDICAO}")
    '''
    return query_api.query(query, org=INFLUX_ORG)
