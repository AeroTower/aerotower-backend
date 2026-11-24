"""CT-SEG-02 (teste individual) — Rotas do Backend sem login.

Ataque: alguem sem conta nenhuma chama a API publica direto (navegador,
curl ou o proprio Swagger em /docs), sem o cabecalho Authorization.
Esperado: HTTP 401 em tudo que le dado pessoal ou comanda equipamento.
Obtido hoje:
  * GET /eventos/interesses devolve os e-mails que os visitantes deixaram
    na loja (dado pessoal: LGPD, art. 46 - medidas de seguranca);
  * POST /motor/desligar, /motor/ciclo e /thresholds (rotas "legado")
    comandam a torre configurada em TORRE_LEGADA e mudam os limites dela.
"""
import pytest

pytestmark = pytest.mark.defeito


def test_lista_de_emails_da_loja_exige_login(app_e_mqtt):
    cliente, _, _ = app_e_mqtt
    cliente.post("/eventos/interesse",
                 json={"email": "visitante@exemplo.com", "produto": "HidroFullkit", "sessao": "s1"})

    r = cliente.get("/eventos/interesses")            # sem Authorization

    assert r.status_code == 401, f"HTTP {r.status_code}: {r.text[:120]}"


@pytest.mark.parametrize("rota, corpo", [
    ("/motor/desligar", None),
    ("/motor/ciclo", {"minutos_ligado": 1, "minutos_desligado": 1440}),
    ("/thresholds", {"phMin": 0, "phMax": 14}),
], ids=["desligar-bomba", "ciclo-bomba", "mudar-limites"])
def test_rotas_legado_que_comandam_a_torre_exigem_login(app_e_mqtt, rota, corpo):
    cliente, mqtt, _ = app_e_mqtt

    r = cliente.post(rota, json=corpo)                 # sem Authorization

    assert r.status_code == 401, f"HTTP {r.status_code}: {r.text[:120]}"
    assert mqtt.publicados == [], f"comando saiu para o broker: {mqtt.publicados}"
