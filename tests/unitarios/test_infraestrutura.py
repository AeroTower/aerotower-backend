"""Testes unitarios dos adaptadores de infraestrutura.

O broker MQTT, o Redis, o InfluxDB e o WebSocket sao trocados por dubles:
o teste confere o que o adaptador faz com eles, sem rede.
"""
import asyncio
import importlib
import io
import json
import logging
from datetime import datetime

import pytest

from app.domain.entities.leitura import ComandoMotor, LeituraAvaliada, LeituraSensores, StatusMotor
from app.domain.exceptions import FalhaNaPublicacao, NaoAutenticado
from app.infrastructure.messaging import mqtt_client, topicos
from app.infrastructure.messaging.mqtt_publicador import MqttPublicador
from app.infrastructure.messaging.mqtt_subscriber import MqttSubscriber
from tests.conftest import MensagemMqtt


# ── Topicos ──────────────────────────────────────────────────

def test_topico_novo_e_topico_da_torre_legada():
    assert topicos.topico("AT-AAAA0001", topicos.SENSORES) == "aerotower/AT-AAAA0001/sensores"
    assert topicos.topico("AT-LEGADO", topicos.MOTOR_COMANDO) == "hidroponia/motor/comando"
    # tipo sem equivalente antigo cai no formato novo, mesmo na torre legada
    assert topicos.topico("AT-LEGADO", topicos.INFO) == "aerotower/AT-LEGADO/info"


def test_assinaturas_incluem_topicos_novos_e_antigos():
    filtros = topicos.assinaturas()
    assert "aerotower/+/sensores" in filtros and "hidroponia/motor/status" in filtros


def test_interpretar_topico_antigo_de_motor():
    assert topicos.interpretar("hidroponia/motor/status") == ("AT-LEGADO", topicos.MOTOR_STATUS)


# ── Cliente MQTT ─────────────────────────────────────────────

class PahoFalso:
    def __init__(self, falha_em=None):
        self.chamadas, self._falha_em = [], falha_em

    def __getattr__(self, nome):
        def metodo(*args, **kwargs):
            self.chamadas.append(nome)
            if nome == self._falha_em:
                raise OSError("rede fora")
        return metodo


def test_criar_cliente_liga_tls_e_senha(monkeypatch):
    falso = PahoFalso()
    monkeypatch.setattr(mqtt_client.mqtt, "Client", lambda: falso)
    monkeypatch.setattr(mqtt_client, "MQTT_TLS", True)
    assert mqtt_client.criar_cliente() is falso
    assert falso.chamadas == ["username_pw_set", "tls_set"]


def test_conectar_e_desconectar_com_sucesso():
    falso = PahoFalso()
    assert mqtt_client.conectar(falso) is True
    mqtt_client.desconectar(falso)
    assert falso.chamadas == ["connect", "loop_start", "loop_stop", "disconnect"]


def test_broker_fora_do_ar_nao_derruba_a_api():
    assert mqtt_client.conectar(PahoFalso(falha_em="connect")) is False
    mqtt_client.desconectar(PahoFalso(falha_em="disconnect"))   # so registra o aviso


def test_publicacao_recusada_pelo_broker_vira_erro():
    class Resultado:
        rc = 4   # MQTT_ERR_NO_CONN

    class Cliente:
        def publish(self, *a, **k):
            return Resultado()

    with pytest.raises(FalhaNaPublicacao):
        MqttPublicador(Cliente()).publicar("AT-AAAA0001", ComandoMotor("desligar"))


# ── Subscriber MQTT ──────────────────────────────────────────

class CasoDeUsoFalso:
    def __init__(self, erro=False):
        self.chamadas, self._erro = [], erro

    def executar(self, *args):
        self.chamadas.append(args)
        if self._erro:
            raise RuntimeError("falhou")


def _subscriber(leitura=None, motor=None, presenca=None):
    return MqttSubscriber(PahoFalso(), leitura or CasoDeUsoFalso(),
                          motor or CasoDeUsoFalso(), presenca or CasoDeUsoFalso())


def test_registrar_liga_os_callbacks():
    sub = _subscriber()
    sub.registrar()
    assert sub._cliente.on_message == sub._on_message


def test_on_connect_assina_os_topicos_so_com_sucesso():
    cliente = PahoFalso()
    _subscriber()._on_connect(cliente, None, None, 0)
    assert cliente.chamadas.count("subscribe") == len(topicos.assinaturas())

    cliente = PahoFalso()
    _subscriber()._on_connect(cliente, None, None, 5)   # senha errada
    assert "subscribe" not in cliente.chamadas


@pytest.mark.parametrize("payload", [b"{nao e json", b"\xff\xfe", b"[1, 2]", b'"texto"'])
def test_payload_invalido_e_descartado(payload):
    leitura = CasoDeUsoFalso()
    _subscriber(leitura=leitura)._on_message(None, None, MensagemMqtt("aerotower/AT-AAAA0001/sensores", payload))
    assert leitura.chamadas == []


def test_payload_vazio_vira_objeto_vazio():
    presenca = CasoDeUsoFalso()
    _subscriber(presenca=presenca)._on_message(None, None, MensagemMqtt("aerotower/AT-AAAA0001/status", b""))
    assert presenca.chamadas == [("AT-AAAA0001", "status", {})]


def test_status_do_motor_vai_para_o_caso_de_uso_certo():
    motor = CasoDeUsoFalso()
    _subscriber(motor=motor)._on_message(
        None, None, MensagemMqtt("aerotower/AT-AAAA0001/motor/status", b'{"ligado": true}'))
    assert motor.chamadas == [("AT-AAAA0001", {"ligado": True})]


def test_erro_no_processamento_nao_derruba_a_thread_do_mqtt():
    _subscriber(leitura=CasoDeUsoFalso(erro=True))._on_message(
        None, None, MensagemMqtt("aerotower/AT-AAAA0001/sensores", b'{"ph": 6}'))
    _subscriber()._on_disconnect(None, None, 7)


# ── InfluxDB (historico) ─────────────────────────────────────

def test_influx_sem_configuracao_recusa_gravar():
    from app.infrastructure.persistence import influx
    with pytest.raises(RuntimeError):
        influx.write_sensor_reading({"ph": 6})
    with pytest.raises(RuntimeError):
        influx.get_recent_readings()


def test_influx_grava_so_campos_numericos(monkeypatch):
    from app.infrastructure.persistence import influx

    class Api:
        def __init__(self):
            self.gravados, self.consultas = [], []

        def write(self, bucket, record):
            self.gravados.append(record)

        def query(self, consulta, org):
            self.consultas.append(consulta)
            return ["linha"]

    api = Api()
    monkeypatch.setattr(influx, "client", object())
    monkeypatch.setattr(influx, "write_api", api)
    monkeypatch.setattr(influx, "query_api", api)
    influx.write_sensor_reading({"ph": 6.1, "status": "ok", "tds": 500}, device="AT-AAAA0001")
    linha = api.gravados[0].to_line_protocol()
    assert "device=AT-AAAA0001" in linha and "ph=6.1" in linha and "status" not in linha
    assert influx.get_recent_readings(hours=3) == ["linha"]
    assert "-3h" in api.consultas[0]


def test_historico_avisa_uma_vez_e_engole_erros(monkeypatch, caplog):
    from app.infrastructure.persistence import influx
    from app.infrastructure.persistence.historico_influx import HistoricoInflux

    historico = HistoricoInflux()
    with caplog.at_level(logging.INFO):
        historico.registrar("AT-AAAA0001", {"ph": 6})
        historico.registrar("AT-AAAA0001", {"ph": 6})
    assert caplog.text.count("histórico desligado") == 1

    def explode(*a, **k):
        raise ConnectionError("influx fora")

    monkeypatch.setattr(influx, "client", object())
    monkeypatch.setattr(influx, "write_sensor_reading", explode)
    historico.registrar("AT-AAAA0001", {"ph": 6})   # nao propaga

    gravados = []
    monkeypatch.setattr(influx, "write_sensor_reading", lambda d, device: gravados.append(device))
    historico.registrar("AT-AAAA0001", {"ph": 6})
    assert gravados == ["AT-AAAA0001"]


# ── Estado no Redis ──────────────────────────────────────────

class RedisFalso:
    def __init__(self):
        self.dados = {}

    def ping(self):
        return True

    def set(self, chave, valor):
        self.dados[chave] = valor

    def get(self, chave):
        return self.dados.get(chave)


@pytest.fixture()
def estado_redis(monkeypatch):
    from app.infrastructure.state import estado_redis as modulo
    falso = RedisFalso()
    monkeypatch.setattr(modulo.redis, "from_url", lambda url, decode_responses: falso)
    return modulo.EstadoRedis("redis://teste"), falso


def test_redis_vazio_devolve_none(estado_redis):
    estado, _ = estado_redis
    assert estado.ultima_leitura("AT-AAAA0001") is None
    assert estado.ultimo_status_motor("AT-AAAA0001") is None


def test_redis_guarda_e_le_leitura_e_motor(estado_redis):
    estado, falso = estado_redis
    agora = datetime(2026, 11, 21, 16, 0)
    estado.salvar_leitura("AT-AAAA0001", LeituraAvaliada(LeituraSensores({"ph": 6}, agora), ["x"]))
    estado.salvar_status_motor("AT-AAAA0001", StatusMotor({"ligado": True}, None))
    assert "aerotower:AT-AAAA0001:leitura" in falso.dados

    leitura = estado.ultima_leitura("AT-AAAA0001")
    assert leitura.leitura.bruto == {"ph": 6} and leitura.leitura.recebido_em == agora
    assert leitura.alertas == ["x"]
    motor = estado.ultimo_status_motor("AT-AAAA0001")
    assert motor.bruto == {"ligado": True} and motor.recebido_em is None


def test_redis_thresholds_sobrevivem_a_restart(estado_redis, monkeypatch):
    from app.infrastructure.state import estado_redis as modulo
    estado, falso = estado_redis
    t = estado.thresholds("AT-AAAA0001")
    t.aplicar({"phMax": 7.0})
    estado.salvar_thresholds("AT-AAAA0001", t)

    novo = modulo.EstadoRedis("redis://teste")      # "restart" do Backend
    assert novo.thresholds("AT-AAAA0001").ph_max == 7.0
    assert novo.presenca("AT-AAAA0001") is novo.presenca("AT-AAAA0001")
    assert json.loads(falso.dados["aerotower:AT-AAAA0001:thresholds"])["phMax"] == 7.0


# ── Estado em memoria ────────────────────────────────────────

def test_estado_em_memoria_separa_por_torre():
    from app.infrastructure.state.estado_memoria import EstadoEmMemoria
    estado = EstadoEmMemoria()
    estado.salvar_status_motor("AT-AAAA0001", StatusMotor({"ligado": True}))
    assert estado.ultimo_status_motor("AT-AAAA0001").bruto == {"ligado": True}
    assert estado.ultimo_status_motor("AT-BBBB0002") is None
    estado.salvar_thresholds("AT-AAAA0001", estado.thresholds("AT-AAAA0001"))   # nao faz nada
    assert estado.presenca("AT-AAAA0001").online is None


# ── Fotos em disco ───────────────────────────────────────────

def test_fotos_salvar_e_remover(tmp_path, monkeypatch):
    from app.infrastructure.storage import filesystem_foto_storage as modulo
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(modulo, "DIRETORIO_FOTOS", "static/fotos")
    fotos = modulo.FilesystemFotoStorage()
    url = asyncio.run(fotos.salvar(b"imagem", "png"))
    caminho = tmp_path / url.lstrip("/")
    assert caminho.read_bytes() == b"imagem"

    fotos.remover(None)                       # nada a fazer
    fotos.remover("/static/fotos/nao-existe.png")
    fotos.remover(url)
    assert not caminho.exists()


def test_falha_ao_remover_foto_so_gera_aviso(monkeypatch, tmp_path):
    from app.infrastructure.storage import filesystem_foto_storage as modulo
    monkeypatch.chdir(tmp_path)
    (tmp_path / "f.png").write_bytes(b"x")

    def negado(caminho):
        raise PermissionError("somente leitura")

    monkeypatch.setattr(modulo.os, "remove", negado)
    modulo.FilesystemFotoStorage().remover("/f.png")
    assert (tmp_path / "f.png").exists()


# ── WebSocket ────────────────────────────────────────────────

class SocketFalso:
    def __init__(self, cai=False):
        self.recebidos, self._cai = [], cai

    async def send_json(self, payload):
        if self._cai:
            raise RuntimeError("conexao fechada")
        self.recebidos.append(payload)


def test_notificador_sem_event_loop_nao_faz_nada():
    from app.infrastructure.notifications.websocket_notificador import WebSocketNotificador
    WebSocketNotificador().notificar("AT-AAAA0001", {"x": 1})


def test_notificador_entrega_so_a_quem_acompanha_e_remove_quem_caiu():
    from app.infrastructure.notifications.websocket_notificador import WebSocketNotificador
    notificador = WebSocketNotificador()
    meu, outro, caido = SocketFalso(), SocketFalso(), SocketFalso(cai=True)
    notificador.registrar(meu, ["AT-AAAA0001"])
    notificador.registrar(outro, ["AT-BBBB0002"])
    notificador.registrar(caido, ["AT-AAAA0001"])

    asyncio.run(notificador._transmitir("AT-AAAA0001", {"ph": 6}))
    assert meu.recebidos == [{"ph": 6}] and outro.recebidos == []
    assert caido not in notificador._clientes


# ── Validador de sessao (JWT) ────────────────────────────────

def test_sem_segredo_nenhum_login_e_aceito():
    from app.infrastructure.auth.jwt_validador import JwtValidador
    with pytest.raises(NaoAutenticado, match="JWT_SEGREDO"):
        JwtValidador("").validar("qualquer.coisa.aqui")


def test_token_malformado():
    from app.infrastructure.auth.jwt_validador import JwtValidador
    with pytest.raises(NaoAutenticado, match="inválida"):
        JwtValidador("segredo").validar("isto-nao-e-jwt")


# ── Configuracao e log ───────────────────────────────────────

def test_url_postgres_do_render_e_corrigida(monkeypatch):
    from app.core import config
    monkeypatch.setenv("DATABASE_URL", "postgres://u:s@host/banco")
    try:
        assert importlib.reload(config).DATABASE_URL == "postgresql://u:s@host/banco"
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_log_troca_para_utf8_em_terminal_sem_acento(monkeypatch):
    from app.core import logging_config
    bruto = io.BytesIO()
    terminal = io.TextIOWrapper(bruto, encoding="ascii")
    monkeypatch.setattr(logging_config.sys, "stdout", terminal)
    raiz = logging.getLogger()
    anteriores = list(raiz.handlers)
    try:
        logging_config.configurar_logging()
        assert terminal.encoding == "utf-8"
    finally:
        raiz.handlers[:] = anteriores


# ── Modulos de compatibilidade e migracao ────────────────────

def test_modulos_antigos_da_raiz_reexportam_os_novos():
    import database
    import influx
    from app.infrastructure.persistence import database as novo_db
    from app.infrastructure.persistence import influx as novo_influx
    assert database.engine is novo_db.engine
    assert influx.write_sensor_reading is novo_influx.write_sensor_reading


def test_influx_configurado_cria_o_cliente(monkeypatch):
    from app.infrastructure.persistence import influx
    for nome, valor in {"INFLUX_URL": "http://influx:8086", "INFLUX_TOKEN": "t",
                        "INFLUX_ORG": "o", "INFLUX_BUCKET": "b"}.items():
        monkeypatch.setenv(nome, valor)
    try:
        assert importlib.reload(influx).client is not None
    finally:
        monkeypatch.undo()
        importlib.reload(influx)
    assert influx.client is None


def test_migracao_em_banco_novo_nao_faz_nada(tmp_path):
    from sqlalchemy import create_engine, inspect
    from app.infrastructure.persistence import migracoes
    engine = create_engine(f"sqlite:///{tmp_path}/novo.db")
    migracoes.aplicar(engine)
    assert inspect(engine).get_table_names() == []
