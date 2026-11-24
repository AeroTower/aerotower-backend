"""CT-FUNC-02 (teste individual) — Comando para torre desligada.

Cenario (pela API, como o app faz): a torre esta sem energia ou sem
Wi-Fi. O Backend sabe disso (topico status = "offline", campo online:
false na propria API). O dono pede um ciclo da bomba.
Esperado: a API avisa que a torre esta offline (HTTP 409) e nao finge
que deu certo. O comando vai com QoS 1 mas sem "retain", e a torre
conecta com sessao limpa: se ela esta fora, o broker descarta o comando.
Obtido hoje: HTTP 200 "Ciclo iniciado: 10 min ligado / 20 min desligado",
o app mostra sucesso e a torre nunca recebe nada.
"""
import pytest

from tests.apoio import publicar, torre_de

pytestmark = pytest.mark.defeito


def test_ciclo_para_torre_offline_avisa_em_vez_de_fingir_sucesso(app_e_mqtt):
    cliente, mqtt, container = app_e_mqtt
    torre, dono = torre_de(cliente, "dona-offline")
    publicar(container, f"aerotower/{torre}/status", {"status": "offline"})
    assert cliente.get(f"/torres/{torre}", headers=dono).json()["online"] is False

    r = cliente.post(f"/torres/{torre}/motor/ciclo", headers=dono,
                     json={"minutos_ligado": 10, "minutos_desligado": 20})

    assert r.status_code == 409, f"API respondeu {r.status_code}: {r.json()}"
    assert "offline" in r.json()["detail"].lower()
    assert mqtt.publicados == [], "comando foi publicado para uma torre que nao esta ouvindo"
