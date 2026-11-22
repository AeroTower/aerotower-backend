"""Testes do repositorio de torres (tabela `torres`).

O ponto mais delicado e o controle de versao: o servico de auth manda
eventos que podem chegar repetidos ou fora de ordem, e o banco so pode
aceitar o mais novo (a nao ser com forcar=True).
"""
from app.domain.entities.kit import Kit
from app.domain.entities.torre import Torre
from app.infrastructure.persistence.models import TorreModel
from app.infrastructure.persistence.sqlalchemy_torre_repository import (
    SqlAlchemyTorreRepository,
)

ID = "AT-24DCC3A1B2C4"


def _torre(kit=Kit.BASICO, dono=None, apelido=None, id=ID):
    return Torre(id=id, kit=kit, dono_id=dono, apelido=apelido)


def test_aplicar_estado_cria_torre_nova(session):
    repo = SqlAlchemyTorreRepository(session)

    aplicou = repo.aplicar_estado(_torre(Kit.PRO, apelido="Varanda"), versao=1)

    assert aplicou is True
    torre = repo.buscar(ID)
    assert torre.kit is Kit.PRO
    assert torre.apelido == "Varanda"
    assert torre.criada_em is not None
    assert torre.ativada is False          # ainda sem dono


def test_buscar_torre_inexistente_devolve_none(session):
    assert SqlAlchemyTorreRepository(session).buscar("AT-NAOEXISTE") is None


def test_versao_mais_nova_atualiza(session):
    repo = SqlAlchemyTorreRepository(session)
    repo.aplicar_estado(_torre(Kit.BASICO), versao=1)

    assert repo.aplicar_estado(_torre(Kit.COMPLETO), versao=2) is True
    assert repo.buscar(ID).kit is Kit.COMPLETO


def test_evento_repetido_ou_velho_e_ignorado(session, nova_sessao):
    repo = SqlAlchemyTorreRepository(session)
    repo.aplicar_estado(_torre(Kit.PRO), versao=5)

    assert repo.aplicar_estado(_torre(Kit.BASICO), versao=5) is False   # repetido
    assert repo.aplicar_estado(_torre(Kit.BASICO), versao=3) is False   # fora de ordem

    salvo = nova_sessao().get(TorreModel, ID)
    assert salvo.kit == "pro"
    assert salvo.versao == 5


def test_forcar_aceita_versao_menor(session):
    """Reenvio do admin: vale mesmo com versao menor."""
    repo = SqlAlchemyTorreRepository(session)
    repo.aplicar_estado(_torre(Kit.PRO), versao=5)

    assert repo.aplicar_estado(_torre(Kit.BASICO), versao=2, forcar=True) is True
    assert repo.buscar(ID).kit is Kit.BASICO


def test_ativada_em_preenche_ao_ganhar_dono_e_limpa_ao_perder(session):
    repo = SqlAlchemyTorreRepository(session)
    repo.aplicar_estado(_torre(), versao=1)
    assert repo.buscar(ID).ativada_em is None

    repo.aplicar_estado(_torre(dono="caio"), versao=2)
    ativada = repo.buscar(ID)
    assert ativada.ativada_em is not None
    assert ativada.pertence_a("caio")

    repo.aplicar_estado(_torre(dono=None), versao=3)
    assert repo.buscar(ID).ativada_em is None


def test_ativada_em_nao_muda_se_dono_continua_o_mesmo(session):
    repo = SqlAlchemyTorreRepository(session)
    repo.aplicar_estado(_torre(dono="caio"), versao=1)
    primeira = repo.buscar(ID).ativada_em

    repo.aplicar_estado(_torre(dono="caio", apelido="Novo nome"), versao=2)

    assert repo.buscar(ID).ativada_em == primeira


def test_listar_do_dono_traz_so_as_torres_dele(session):
    repo = SqlAlchemyTorreRepository(session)
    repo.aplicar_estado(_torre(id="AT-AAAA1111", dono="caio"), versao=1)
    repo.aplicar_estado(_torre(id="AT-BBBB2222", dono="caio"), versao=1)
    repo.aplicar_estado(_torre(id="AT-CCCC3333", dono="rafael"), versao=1)

    ids = {t.id for t in repo.listar_do_dono("caio")}

    assert ids == {"AT-AAAA1111", "AT-BBBB2222"}
