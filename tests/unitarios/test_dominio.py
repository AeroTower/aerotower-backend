"""Testes unitarios das entidades e servicos de dominio (sem banco, sem rede)."""
import pytest

from app.domain import exceptions as exc
from app.domain.entities.kit import Kit, capacidades_do_kit, filtrar_por_capacidades
from app.domain.entities.leitura import ComandoMotor, LeituraSensores
from app.domain.entities.thresholds import Thresholds
from app.domain.entities.torre import Torre, id_de_torre_valido
from app.domain.services.avaliador_alertas import ACIMA, REGRAS, AvaliadorDeAlertas, RegraDeAlerta
from app.domain.services.validador_evento import ValidadorDeEvento


# ── Thresholds ─────────────────────────────────────────────

def test_thresholds_to_dict_usa_os_nomes_do_app():
    assert Thresholds().to_dict() == {
        "phMin": 5.5, "phMax": 6.5, "ecMin": 0.8, "ecMax": 1.8,
        "temperaturaAguaMax": 28, "temperaturaAmbienteMax": 32,
        "umidadeRelativaMin": 45, "nivelAguaMin": 35,
    }


def test_thresholds_aplicar_ignora_campo_desconhecido_e_valor_nulo():
    t = Thresholds()
    t.aplicar({"phMin": 5.0, "phMax": None, "campoQueNaoExiste": 99})
    assert t.ph_min == 5.0
    assert t.ph_max == 6.5            # None nao apaga o valor
    assert not hasattr(t, "campoQueNaoExiste")


# ── Leitura ─────────────────────────────────────────────────

def test_ec_e_calculado_a_partir_do_tds_quando_nao_vem():
    assert LeituraSensores(bruto={"tds": 600}).ec == 1.2


def test_ec_enviado_tem_prioridade_sobre_tds():
    assert LeituraSensores(bruto={"ec": 1.5, "tds": 600}).ec == 1.5


def test_booleano_e_texto_nao_viram_numero():
    leitura = LeituraSensores(bruto={"ph": True, "nivelAgua": "cheio"})
    assert leitura.ph is None
    assert leitura.nivel_agua is None


def test_nomes_antigos_do_firmware_ainda_sao_lidos():
    leitura = LeituraSensores(bruto={"temperatura": 25.5, "umidade": 61})
    assert leitura.temperatura_ambiente == 25.5
    assert leitura.umidade_relativa == 61


def test_sem_nenhum_nome_de_umidade_devolve_none():
    assert LeituraSensores(bruto={}).umidade_relativa is None


def test_comando_de_ciclo_e_de_desligar():
    assert ComandoMotor("ciclo", 10, 50).to_payload() == {
        "acao": "ciclo", "minutos_ligado": 10, "minutos_desligado": 50}
    assert ComandoMotor("desligar").to_payload() == {"acao": "desligar"}


# ── Avaliador de alertas (todas as faixas) ──────────────────

@pytest.mark.parametrize("bruto, trecho", [
    ({"ph": 4.0}, "pH abaixo"),
    ({"ph": 8.0}, "pH acima"),
    ({"ec": 0.1}, "EC abaixo"),
    ({"ec": 3.0}, "EC acima"),
    ({"temperaturaAgua": 31}, "Temperatura da água alta"),
    ({"temperaturaAmbiente": 40}, "Temperatura ambiente alta"),
    ({"umidadeRelativa": 20}, "Umidade relativa baixa"),
    ({"nivelAgua": 10}, "Nível de água baixo"),
])
def test_cada_sensor_fora_da_faixa_gera_alerta(bruto, trecho):
    alertas = AvaliadorDeAlertas().avaliar(LeituraSensores(bruto=bruto), Thresholds())
    assert len(alertas) == 1 and trecho in alertas[0]


def test_leitura_dentro_da_faixa_nao_gera_alerta():
    bruto = {"ph": 6.0, "ec": 1.2, "temperaturaAgua": 22, "temperaturaAmbiente": 25,
             "umidadeRelativa": 60, "nivelAgua": 80}
    assert AvaliadorDeAlertas().avaliar(LeituraSensores(bruto=bruto), Thresholds()) == []


def test_valor_no_limite_exato_nao_e_alerta():
    t = Thresholds()
    bruto = {"ph": t.ph_min, "nivelAgua": t.nivel_agua_min}
    assert AvaliadorDeAlertas().avaliar(LeituraSensores(bruto=bruto), t) == []



def test_mensagem_do_alerta_mantem_o_formato_antigo():
    # A refatoracao trocou os if por uma tabela; o texto que o app mostra nao muda.
    alertas = AvaliadorDeAlertas().avaliar(
        LeituraSensores(bruto={"ph": 4.5, "temperaturaAgua": 31.5}), Thresholds())
    assert alertas == ["pH abaixo do limite: 4.5", "Temperatura da água alta: 31.5°C"]


def test_cada_regra_aponta_para_campos_que_existem():
    leitura, limites = LeituraSensores(bruto={}), Thresholds()
    for regra in REGRAS:
        assert hasattr(leitura, regra.campo), regra.campo
        assert hasattr(limites, regra.limite), regra.limite


def test_regra_nova_entra_sem_mudar_o_avaliador():
    regra = RegraDeAlerta("ph", "ph_max", ACIMA, "pH alto demais: {valor}")
    alertas = AvaliadorDeAlertas(regras=[regra]).avaliar(LeituraSensores(bruto={"ph": 9}), Thresholds())
    assert alertas == ["pH alto demais: 9"]

# ── Kit e torre ──────────────────────────────────────────────

def test_capacidades_de_cada_kit():
    assert capacidades_do_kit(Kit.BASICO) == ["bomba"]
    assert capacidades_do_kit(Kit.COMPLETO) == ["bomba", "nivel"]
    assert "ph" in capacidades_do_kit(Kit.PRO)


def test_torre_desconhecida_nao_tem_nada_filtrado():
    dados = {"ph": 6, "motor": True}
    assert filtrar_por_capacidades(dados, None) == dados


def test_kit_completo_mede_nivel_mas_nao_ph():
    filtrado = filtrar_por_capacidades({"ph": 6, "nivelAgua": 50, "motor": True},
                                       capacidades_do_kit(Kit.COMPLETO))
    assert filtrado == {"nivelAgua": 50, "motor": True}


@pytest.mark.parametrize("torre_id, valido", [
    ("AT-24DCC3A1B2C4", True),
    ("AT-SIMDEMO01", True),
    ("AT-123", False),               # curto demais
    ("at-24dcc3a1b2c4", False),      # minusculo (o caso de uso converte antes)
    ("XX-24DCC3A1B2C4", False),
    ("AT-24DC/../C4", False),
    ("", False),
    (None, False),
])
def test_formato_do_id_da_torre(torre_id, valido):
    assert id_de_torre_valido(torre_id) is valido


def test_torre_sem_dono_nao_pertence_a_ninguem():
    torre = Torre(id="AT-AAAA1111", kit=Kit.PRO)
    assert torre.ativada is False
    assert torre.pertence_a("maria") is False
    torre.dono_id = "maria"
    assert torre.ativada and torre.pertence_a("maria") and not torre.pertence_a("joao")


# ── Validador de eventos da loja ─────────────────────────────

def test_evento_valido_passa():
    ValidadorDeEvento().validar_evento("cta_diy", "/diy", "sessao-1")


@pytest.mark.parametrize("nome, pagina, sessao", [
    ("cta_hackeado", "/", "s"),        # fora da lista fechada
    ("cta_diy", "/", ""),              # sem sessao
    ("cta_diy", "/", "s" * 201),       # sessao longa
    ("cta_diy", "/" * 201, "s"),       # pagina longa
])
def test_evento_invalido_e_recusado(nome, pagina, sessao):
    with pytest.raises(exc.EventoInvalido):
        ValidadorDeEvento().validar_evento(nome, pagina, sessao)


def test_email_do_interesse_e_normalizado():
    assert ValidadorDeEvento().validar_interesse("  Ana@Exemplo.COM ", "pro", "s") == "ana@exemplo.com"


@pytest.mark.parametrize("email", ["sem-arroba", "a@b", "a b@c.com", "x@" + "a" * 200 + ".com"])
def test_email_invalido(email):
    with pytest.raises(exc.EmailInvalido):
        ValidadorDeEvento().validar_interesse(email, "pro", "s")


@pytest.mark.parametrize("produto, sessao", [("", "s"), ("p" * 201, "s"), ("pro", ""), ("pro", "s" * 201)])
def test_interesse_sem_produto_ou_sessao(produto, sessao):
    with pytest.raises(exc.EventoInvalido):
        ValidadorDeEvento().validar_interesse("ana@exemplo.com", produto, sessao)


# ── Excecoes de dominio ──────────────────────────────────────

def test_mensagens_das_excecoes():
    assert "7" in str(exc.PlantaNaoEncontrada(7))
    assert exc.FormatoDeFotoInvalido(["jpg"]).extensoes_aceitas == ["jpg"]
    assert "42" in str(exc.FalhaNaPublicacao(42))
    assert exc.EmailInvalido("x").email == "x"
    assert str(exc.NenhumDadoDisponivel("nada")) == "nada"
    assert str(exc.NaoAutenticado()) == "Login necessário."
    assert str(exc.AcessoNegado()) == "Acesso negado."
    assert exc.TorreNaoEncontrada("AT-1").torre_id == "AT-1"
    assert "AT-<MAC>" in str(exc.IdDeTorreInvalido("x"))


# ── Faixas fisicas (sensor com defeito) e limites invalidos ─────────

@pytest.mark.parametrize("valor", ["seis", float("nan"), float("inf"), True])
def test_thresholds_recusa_limite_que_nao_e_numero(valor):
    limites = Thresholds()
    with pytest.raises(exc.LimitesInvalidos):
        limites.aplicar({"phMin": valor})
    assert limites.ph_min == 5.5


def test_thresholds_aceita_mudanca_coerente_e_valida_o_par_inteiro():
    limites = Thresholds()
    limites.aplicar({"phMin": 6.0, "phMax": 7.0})
    assert (limites.ph_min, limites.ph_max) == (6.0, 7.0)
    with pytest.raises(exc.LimitesInvalidos, match="menor que phMax"):
        limites.aplicar({"phMin": 7.5})          # passaria do maximo ja gravado


@pytest.mark.parametrize("dados, esperado", [
    ({"umidadeRelativa": 130}, "Sensor de umidade"),
    ({"nivelAgua": -5}, "Sensor de nível"),
])
def test_leitura_impossivel_vira_alerta_de_sensor_e_nao_de_limite(dados, esperado):
    alertas = AvaliadorDeAlertas().avaliar(LeituraSensores(bruto=dados), Thresholds())
    assert len(alertas) == 1 and alertas[0].startswith(esperado)


def test_leitura_nan_vira_sem_leitura():
    assert LeituraSensores(bruto={"ph": float("nan")}).ph is None
