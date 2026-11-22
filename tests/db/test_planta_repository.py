"""Testes do repositorio de plantas (tabela `plantas`, PostgreSQL/SQLite)."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.entities.planta import Planta
from app.infrastructure.persistence.models import PlantaModel
from app.infrastructure.persistence.sqlalchemy_planta_repository import (
    SqlAlchemyPlantaRepository,
)

TORRE = "AT-24DCC3A1B2C4"
OUTRA_TORRE = "AT-AAAABBBB"
CAIO = "google-sub-caio"
FERNAO = "google-sub-fernao"


def _planta(nome="Alface", torre=TORRE, usuario=CAIO, **extra):
    return Planta(
        nome=nome, tipo="folhosa", data_plantio="2026-10-01",
        torre_id=torre, usuario_id=usuario, **extra,
    )


# ── Criar e ler ───────────────────────────────────────────

def test_criar_gera_id_e_persiste_todos_os_campos(session, nova_sessao):
    repo = SqlAlchemyPlantaRepository(session)

    criada = repo.criar(_planta(foto_url="/static/fotos/a.jpg"))

    assert criada.id is not None
    # Le por OUTRA sessao: prova que o commit chegou no banco.
    salva = nova_sessao().get(PlantaModel, criada.id)
    assert salva.nome == "Alface"
    assert salva.tipo == "folhosa"
    assert salva.data_plantio == "2026-10-01"
    assert salva.foto_url == "/static/fotos/a.jpg"
    assert salva.torre_id == TORRE
    assert salva.usuario_id == CAIO


def test_foto_e_opcional(session):
    criada = SqlAlchemyPlantaRepository(session).criar(_planta())
    assert criada.foto_url is None


def test_nome_obrigatorio_e_barrado_pelo_banco(session):
    # nullable=False no modelo: o proprio banco recusa.
    session.add(PlantaModel(nome=None, tipo="folhosa", data_plantio="2026-10-01"))
    with pytest.raises(IntegrityError):
        session.commit()


# ── Isolamento por torre E por usuario ────────────────────

def test_listar_so_traz_plantas_do_usuario_naquela_torre(session):
    repo = SqlAlchemyPlantaRepository(session)
    repo.criar(_planta("Alface"))                          # Caio, torre 1
    repo.criar(_planta("Manjericao"))                      # Caio, torre 1
    repo.criar(_planta("Rucula", usuario=FERNAO))          # outro usuario
    repo.criar(_planta("Hortela", torre=OUTRA_TORRE))      # outra torre

    nomes = [p.nome for p in repo.listar(TORRE, CAIO)]

    assert nomes == ["Alface", "Manjericao"]


def test_listar_vem_em_ordem_de_cadastro(session):
    repo = SqlAlchemyPlantaRepository(session)
    for nome in ["C", "A", "B"]:
        repo.criar(_planta(nome))
    assert [p.nome for p in repo.listar(TORRE, CAIO)] == ["C", "A", "B"]


def test_listar_vazio_devolve_lista_vazia(session):
    assert SqlAlchemyPlantaRepository(session).listar(TORRE, CAIO) == []


def test_buscar_planta_de_outro_usuario_devolve_none(session):
    """Seguranca: saber o id da planta nao basta para ver a planta alheia."""
    repo = SqlAlchemyPlantaRepository(session)
    da_fernao = repo.criar(_planta(usuario=FERNAO))

    assert repo.buscar_por_id(da_fernao.id, TORRE, CAIO) is None
    assert repo.buscar_por_id(da_fernao.id, TORRE, FERNAO) is not None


def test_buscar_id_inexistente_devolve_none(session):
    assert SqlAlchemyPlantaRepository(session).buscar_por_id(999, TORRE, CAIO) is None


# ── Remover ───────────────────────────────────────────────

def test_remover_apaga_do_banco(session, nova_sessao):
    repo = SqlAlchemyPlantaRepository(session)
    planta = repo.criar(_planta())

    repo.remover(planta.id)

    assert nova_sessao().get(PlantaModel, planta.id) is None


def test_remover_id_inexistente_nao_quebra(session):
    SqlAlchemyPlantaRepository(session).remover(12345)  # nao deve lancar erro


def test_remover_nao_afeta_as_outras_plantas(session):
    repo = SqlAlchemyPlantaRepository(session)
    a = repo.criar(_planta("A"))
    repo.criar(_planta("B"))

    repo.remover(a.id)

    assert [p.nome for p in repo.listar(TORRE, CAIO)] == ["B"]


def test_sessao_continua_utilizavel_depois_de_erro(session):
    """Refatoracao: _commit() faz rollback quando o commit falha. Sem isso,
    a sessao ficava travada e ate uma consulta simples dava erro."""
    repo = SqlAlchemyPlantaRepository(session)
    with pytest.raises(IntegrityError):
        repo.criar(Planta(nome=None, tipo="folhosa", data_plantio="2026-10-01"))

    assert repo.criar(_planta("Depois do erro")).id is not None
