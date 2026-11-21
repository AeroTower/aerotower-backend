"""Testes unitarios dos casos de uso.

Cada caso de uso recebe dubles ("stubs") no lugar do banco, do MQTT e do
WebSocket: o teste exercita so a regra, sem nenhuma dependencia externa.
"""
import asyncio

import pytest

from app.application.use_cases.atualizar_thresholds import AtualizarThresholds
from app.application.use_cases.buscar_planta import BuscarPlanta
from app.application.use_cases.criar_planta import CriarPlanta
from app.application.use_cases.obter_alertas import ObterAlertas
from app.application.use_cases.obter_resumo_validacao import (
    ExportarEventos,
    ListarInteresses,
    ObterResumoValidacao,
)
from app.application.use_cases.obter_status_motor import ObterStatusMotor
from app.application.use_cases.obter_thresholds import ObterThresholds
from app.application.use_cases.obter_ultima_leitura import ObterUltimaLeitura
from app.application.use_cases.processar_leitura import ProcessarLeitura
from app.application.use_cases.processar_status_motor import ProcessarStatusMotor
from app.application.use_cases.registrar_evento import RegistrarEvento
from app.application.use_cases.registrar_interesse import RegistrarInteresse
from app.application.use_cases.sincronizar_torre import SincronizarTorre
from app.domain.entities.evento import ResumoValidacao
from app.domain.entities.kit import Kit
from app.domain.entities.leitura import LeituraAvaliada, LeituraSensores, StatusMotor
from app.domain.exceptions import (
    EmailInvalido,
    EventoInvalido,
    FormatoDeFotoInvalido,
    IdDeTorreInvalido,
    NenhumDadoDisponivel,
    PlantaNaoEncontrada,
)
from app.domain.services.avaliador_alertas import AvaliadorDeAlertas
from app.domain.services.validador_evento import ValidadorDeEvento
from app.infrastructure.state.estado_memoria import EstadoEmMemoria


# ── Dubles de teste ─────────────────────────────────────────

class NotificadorFalso:
    def __init__(self):
        self.enviados = []

    def notificar(self, torre_id, payload):
        self.enviados.append((torre_id, payload))


class CatalogoFalso:
    def __init__(self, capacidades=None):
        self._capacidades = capacidades

    def capacidades(self, torre_id):
        return self._capacidades


class HistoricoFalso:
    def __init__(self):
        self.gravados = []

    def registrar(self, torre_id, dados):
        self.gravados.append((torre_id, dados))


class RepositorioDePlantasFalso:
    def __init__(self):
        self.criadas = []

    def criar(self, planta):
        planta.id = len(self.criadas) + 1
        self.criadas.append(planta)
        return planta

    def buscar_por_id(self, planta_id, torre_id, usuario_id):
        return None


class ArmazenamentoFalso:
    def __init__(self):
        self.salvos = []

    def extensoes_aceitas(self):
        return ["jpg", "png"]

    async def salvar(self, conteudo, extensao):
        self.salvos.append((conteudo, extensao))
        return f"/static/fotos/x.{extensao}"


class RepositorioDeEventosFalso:
    def __init__(self):
        self.eventos, self.interesses = [], []

    def registrar_evento(self, evento):
        self.eventos.append(evento)
        return evento

    def registrar_interesse(self, interesse):
        self.interesses.append(interesse)
        return interesse

    def resumo(self):
        return ResumoValidacao(eventos=[], total_interesses=len(self.interesses), total_sessoes=0)

    def listar_interesses(self):
        return list(self.interesses)

    def listar_eventos(self):
        return list(self.eventos)


class RepositorioDeTorresFalso:
    def __init__(self):
        self.aplicados = []

    def aplicar_estado(self, torre, versao, forcar=False):
        self.aplicados.append((torre, versao, forcar))
        return True


# ── Thresholds ──────────────────────────────────────────────

def test_atualizar_thresholds_muda_so_a_torre_pedida():
    estado = EstadoEmMemoria()
    AtualizarThresholds(estado).executar("AT-AAAA0001", {"phMin": 5.0})
    assert ObterThresholds(estado).executar("AT-AAAA0001").ph_min == 5.0
    assert ObterThresholds(estado).executar("AT-BBBB0002").ph_min == 5.5


# ── Leituras e alertas ──────────────────────────────────────

def test_sem_leitura_nao_ha_alertas_nem_dados():
    estado = EstadoEmMemoria()
    assert ObterAlertas(estado).executar("AT-AAAA0001") == []
    with pytest.raises(NenhumDadoDisponivel):
        ObterUltimaLeitura(estado).executar("AT-AAAA0001")


def test_alertas_vem_da_ultima_leitura():
    estado = EstadoEmMemoria()
    estado.salvar_leitura("AT-AAAA0001", LeituraAvaliada(LeituraSensores(), ["pH alto"]))
    assert ObterAlertas(estado).executar("AT-AAAA0001") == ["pH alto"]


def test_processar_leitura_filtra_avalia_grava_e_notifica():
    estado, notificador, historico = EstadoEmMemoria(), NotificadorFalso(), HistoricoFalso()
    caso = ProcessarLeitura(estado, AvaliadorDeAlertas(), notificador,
                            CatalogoFalso(["bomba", "nivel"]), historico)
    avaliada = caso.executar("AT-AAAA0001", {"ph": 3.0, "nivelAgua": 10, "motor": True})

    assert avaliada.leitura.bruto == {"nivelAgua": 10, "motor": True}   # kit sem pH
    assert avaliada.alertas == ["Nível de água baixo: 10%"]
    assert historico.gravados == [("AT-AAAA0001", {"nivelAgua": 10, "motor": True})]
    torre_id, payload = notificador.enviados[0]
    assert torre_id == "AT-AAAA0001" and payload["alertas"] == avaliada.alertas


def test_processar_leitura_funciona_sem_historico():
    caso = ProcessarLeitura(EstadoEmMemoria(), AvaliadorDeAlertas(), NotificadorFalso(), CatalogoFalso())
    assert caso.executar("AT-AAAA0001", {"ph": 6.0}).alertas == []


# ── Motor ────────────────────────────────────────────────────

def test_status_do_motor_antes_e_depois_de_chegar():
    estado, notificador = EstadoEmMemoria(), NotificadorFalso()
    with pytest.raises(NenhumDadoDisponivel):
        ObterStatusMotor(estado).executar("AT-AAAA0001")

    ProcessarStatusMotor(estado, notificador).executar("AT-AAAA0001", {"ligado": True})
    status = ObterStatusMotor(estado).executar("AT-AAAA0001")
    assert isinstance(status, StatusMotor) and status.bruto == {"ligado": True}
    assert notificador.enviados[0][1]["motorStatus"]["ligado"] is True


# ── Plantas ──────────────────────────────────────────────────

def test_buscar_planta_inexistente():
    with pytest.raises(PlantaNaoEncontrada):
        BuscarPlanta(RepositorioDePlantasFalso()).executar(99, "AT-AAAA0001", "maria")


def test_criar_planta_com_foto_valida_salva_a_foto():
    repo, fotos = RepositorioDePlantasFalso(), ArmazenamentoFalso()
    planta = asyncio.run(CriarPlanta(repo, fotos).executar(
        "Alface", "folhosa", "2026-11-21", "Minha.Foto.PNG", b"bytes", "AT-AAAA0001", "maria"))
    assert planta.foto_url == "/static/fotos/x.png"
    assert fotos.salvos == [(b"bytes", "png")]


def test_criar_planta_recusa_formato_de_foto():
    repo, fotos = RepositorioDePlantasFalso(), ArmazenamentoFalso()
    with pytest.raises(FormatoDeFotoInvalido):
        asyncio.run(CriarPlanta(repo, fotos).executar(
            "Alface", "folhosa", "2026-11-21", "virus.exe", b"MZ"))
    assert repo.criadas == [] and fotos.salvos == []


def test_criar_planta_sem_foto():
    planta = asyncio.run(CriarPlanta(RepositorioDePlantasFalso(), ArmazenamentoFalso())
                         .executar("Rúcula", "folhosa", "2026-11-21"))
    assert planta.foto_url is None


# ── Validacao da loja (eventos e interesse) ──────────────────

def test_registrar_evento_valido_e_invalido():
    repo = RepositorioDeEventosFalso()
    caso = RegistrarEvento(repo, ValidadorDeEvento())
    evento = caso.executar("cta_ver_kits", "/loja", "sessao-1")
    assert evento.criado_em is not None and repo.eventos == [evento]
    with pytest.raises(EventoInvalido):
        caso.executar("qualquer_coisa", "/", "sessao-1")
    assert len(repo.eventos) == 1


def test_registrar_interesse_guarda_email_normalizado():
    repo = RepositorioDeEventosFalso()
    caso = RegistrarInteresse(repo, ValidadorDeEvento())
    assert caso.executar(" Bia@Exemplo.com ", "pro", "s1").email == "bia@exemplo.com"
    with pytest.raises(EmailInvalido):
        caso.executar("bia", "pro", "s1")


def test_resumo_interesses_e_exportacao():
    repo = RepositorioDeEventosFalso()
    RegistrarEvento(repo, ValidadorDeEvento()).executar("cta_diy", "/", "s1")
    RegistrarInteresse(repo, ValidadorDeEvento()).executar("a@b.com", "pro", "s1")
    assert ObterResumoValidacao(repo).executar().total_interesses == 1
    assert [i.email for i in ListarInteresses(repo).executar()] == ["a@b.com"]
    assert [e.nome for e in ExportarEventos(repo).executar()] == ["cta_diy"]


# ── Sincronizacao vinda do servico de auth ───────────────────

def test_sincronizar_converte_id_para_maiusculas():
    repo = RepositorioDeTorresFalso()
    assert SincronizarTorre(repo).executar("at-aaaa0001", Kit.PRO, "maria", None, 2) is True
    torre, versao, forcar = repo.aplicados[0]
    assert torre.id == "AT-AAAA0001" and versao == 2 and forcar is False


@pytest.mark.parametrize("torre_id", ["", None, "torre-1", "AT-../../etc"])
def test_sincronizar_recusa_id_fora_do_padrao(torre_id):
    repo = RepositorioDeTorresFalso()
    with pytest.raises(IdDeTorreInvalido):
        SincronizarTorre(repo).executar(torre_id, Kit.PRO, None, None, 1)
    assert repo.aplicados == []
