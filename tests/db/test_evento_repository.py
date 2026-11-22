"""Testes das tabelas `eventos` e `interesses` (dados do smoke test da loja).

Esses numeros vao para o relatorio (funil de conversao), entao a contagem
precisa estar certa: cliques totais x sessoes distintas.
"""
import time
from datetime import datetime, timedelta

from app.domain.entities.evento import Evento, Interesse
from app.infrastructure.persistence.sqlalchemy_evento_repository import (
    SqlAlchemyEventoRepository,
)

T0 = datetime(2026, 10, 1, 12, 0, 0)


def _evento(nome, sessao, minutos=0):
    return Evento(nome=nome, pagina="/loja", sessao=sessao, criado_em=T0 + timedelta(minutes=minutos))


def _interesse(email, minutos=0):
    return Interesse(email=email, produto="kit-completo", sessao="s1", criado_em=T0 + timedelta(minutes=minutos))


def test_registrar_evento_gera_id(session):
    salvo = SqlAlchemyEventoRepository(session).registrar_evento(_evento("page_view", "s1"))
    assert salvo.id is not None
    assert salvo.criado_em == T0


def test_resumo_separa_cliques_de_sessoes(session):
    """Uma pessoa que clica 5 vezes = 5 cliques, 1 sessao."""
    repo = SqlAlchemyEventoRepository(session)
    for _ in range(5):
        repo.registrar_evento(_evento("clique_me_avise", "sessao-A"))
    repo.registrar_evento(_evento("clique_me_avise", "sessao-B"))
    repo.registrar_evento(_evento("page_view", "sessao-A"))
    repo.registrar_evento(_evento("page_view", "sessao-B"))
    repo.registrar_evento(_evento("page_view", "sessao-C"))

    resumo = repo.resumo()
    por_nome = {c.nome: c for c in resumo.eventos}

    assert por_nome["clique_me_avise"].total == 6
    assert por_nome["clique_me_avise"].sessoes == 2
    assert por_nome["page_view"].total == 3
    assert por_nome["page_view"].sessoes == 3
    assert resumo.total_sessoes == 3            # A, B e C


def test_resumo_ordena_do_evento_mais_frequente(session):
    repo = SqlAlchemyEventoRepository(session)
    repo.registrar_evento(_evento("raro", "s1"))
    for i in range(3):
        repo.registrar_evento(_evento("comum", f"s{i}"))

    assert [c.nome for c in repo.resumo().eventos] == ["comum", "raro"]


def test_resumo_conta_interesses(session):
    repo = SqlAlchemyEventoRepository(session)
    repo.registrar_interesse(_interesse("a@x.com"))
    repo.registrar_interesse(_interesse("b@x.com"))
    assert repo.resumo().total_interesses == 2


def test_resumo_com_banco_vazio_devolve_zeros(session):
    resumo = SqlAlchemyEventoRepository(session).resumo()
    assert resumo.eventos == []
    assert resumo.total_interesses == 0
    assert resumo.total_sessoes == 0


def test_listar_interesses_do_mais_recente_para_o_mais_antigo(session):
    repo = SqlAlchemyEventoRepository(session)
    repo.registrar_interesse(_interesse("antigo@x.com", minutos=0))
    repo.registrar_interesse(_interesse("novo@x.com", minutos=10))

    assert [i.email for i in repo.listar_interesses()] == ["novo@x.com", "antigo@x.com"]


def test_listar_eventos_em_ordem_cronologica(session):
    repo = SqlAlchemyEventoRepository(session)
    repo.registrar_evento(_evento("segundo", "s1", minutos=5))
    repo.registrar_evento(_evento("primeiro", "s1", minutos=0))

    assert [e.nome for e in repo.listar_eventos()] == ["primeiro", "segundo"]


def test_desempenho_resumo_com_mil_eventos(session):
    """Teste de desempenho: o painel de validacao chama resumo() a cada
    acesso. Com 1.000 eventos ele precisa responder bem abaixo de 1 s."""
    repo = SqlAlchemyEventoRepository(session)
    from app.infrastructure.persistence.models import EventoModel
    session.add_all(
        EventoModel(nome=f"evento_{i % 10}", pagina="/loja", sessao=f"s{i % 200}", criado_em=T0)
        for i in range(1000)
    )
    session.commit()

    inicio = time.perf_counter()
    resumo = repo.resumo()
    duracao = time.perf_counter() - inicio

    assert sum(c.total for c in resumo.eventos) == 1000
    assert resumo.total_sessoes == 200
    assert duracao < 1.0, f"resumo() levou {duracao:.3f}s"
