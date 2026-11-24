"""CT-DESEMP-02 (teste individual) — Carga e pico na API do Backend.

Cada usuario virtual e um PAINEL DO APP ABERTO, fazendo o mesmo que o app:
a cada 3 s pede a ultima leitura e o status da bomba; a cada 15 s, o
detalhe da torre (presenca). 1 painel = ~0,7 requisicao por segundo.

Cenarios (variavel CENARIO):
  carga   50 paineis abertos ao mesmo tempo por 4 min (teste de carga)
  pico    10 paineis por 1 min, salto para 200 em 5 s, 2 min no alto,
          volta a 10 por 1 min (teste de spike)
  ensaio  20 paineis por 40 s (so para conferir o roteiro)

Criterios de aprovacao (impressos no fim, com APROVADO/REPROVADO):
  carga: falhas <= 1% e p95 <= 1000 ms
  pico:  falhas <= 1% e p95 <= 2000 ms

Passo a passo para rodar contra a Azure: README.md desta pasta.
"""
import os

import requests
from locust import HttpUser, LoadTestShape, constant, events, task

BACKEND_PADRAO = "https://aerotower-backend-bfb7frgsbccuanhf.eastus-01.azurewebsites.net"
AUTH_PADRAO = "https://aerotower-auth-cxandce6bwcsdshf.eastus-01.azurewebsites.net"

CENARIO = os.getenv("CENARIO", "carga").strip().lower()
CRITERIOS = {"carga": 1000, "pico": 2000, "ensaio": 1000}     # p95 maximo (ms)
ETAPAS = {                                                    # (ate o segundo, paineis, abertos por s)
    "carga":  [(240, 50, 5)],
    "pico":   [(60, 10, 5), (180, 200, 40), (240, 10, 40)],
    "ensaio": [(40, 20, 10)],
}

_sessao = {"token": os.getenv("AEROTOWER_TOKEN", "").strip(),
           "torre": os.getenv("AEROTOWER_TORRE", "").strip().upper()}


@events.test_start.add_listener
def preparar(environment, **_):
    """Consegue um token e uma torre antes de abrir os paineis."""
    if not _sessao["token"]:
        # Sem token: usa o login de teste do auth (o mesmo botao "Entrar sem
        # Google" do app, que so funciona com AUTH_MODO_DEV=true no servidor).
        auth = os.getenv("AEROTOWER_AUTH", AUTH_PADRAO).rstrip("/")
        r = requests.post(f"{auth}/auth/dev", json={"id": "demo"}, timeout=90)
        if r.status_code != 200:
            raise SystemExit(f"Login de teste recusado ({r.status_code}). Defina AEROTOWER_TOKEN "
                             "com o token copiado do navegador (README, passo 3).")
        _sessao["token"] = r.json()["token"]
    if not _sessao["torre"]:
        r = requests.get(f"{environment.host}/torres", timeout=90,
                         headers={"Authorization": f"Bearer {_sessao['token']}"})
        torres = r.json() if r.status_code == 200 else []
        if not torres:
            raise SystemExit(f"A conta nao tem torre (HTTP {r.status_code}). Defina AEROTOWER_TORRE "
                             "e AEROTOWER_TOKEN de uma conta com torre (README, passo 3).")
        _sessao["torre"] = torres[0]["id"]
    print(f"Cenario '{CENARIO}' na torre {_sessao['torre']} em {environment.host}")


class PainelAberto(HttpUser):
    host = os.getenv("AEROTOWER_BACKEND", BACKEND_PADRAO)
    wait_time = constant(3)            # o app atualiza o painel a cada 3 s

    def on_start(self):
        self.ciclos = 0
        self.cabecalho = {"Authorization": f"Bearer {_sessao['token']}"}

    def _pedir(self, caminho, nome):
        with self.client.get(caminho, headers=self.cabecalho, name=nome, catch_response=True) as r:
            # "Nenhum dado recebido ainda" (503 do proprio Backend) = torre sem
            # leitura: o app mostra "aguardando" e nao e sobrecarga. Um 503 da
            # Azure (servidor sem folego) vem sem esse texto e conta como falha.
            sem_leitura = r.status_code in (404, 503) and "ainda" in (r.text or "")
            if r.status_code == 200 or sem_leitura:
                r.success()
            else:
                r.failure(f"HTTP {r.status_code}")

    @task
    def atualizar_painel(self):
        torre = _sessao["torre"]
        self._pedir(f"/torres/{torre}/dados", "/torres/[id]/dados")
        self._pedir(f"/torres/{torre}/motor/status", "/torres/[id]/motor/status")
        if self.ciclos % 5 == 0:       # a cada 15 s
            self._pedir(f"/torres/{torre}", "/torres/[id] (presenca)")
        self.ciclos += 1


class Cenario(LoadTestShape):
    def tick(self):
        agora = self.get_run_time()
        for ate, paineis, por_segundo in ETAPAS[CENARIO]:
            if agora < ate:
                return paineis, por_segundo
        return None


@events.quitting.add_listener
def avaliar(environment, **_):
    total = environment.stats.total
    if not total.num_requests:
        return
    falhas = total.fail_ratio * 100
    p95 = total.get_response_time_percentile(0.95)
    limite = CRITERIOS.get(CENARIO, 1000)
    ok_falhas, ok_p95 = falhas <= 1.0, p95 <= limite
    print("\n================ CT-DESEMP-02 ================")
    print(f"Cenario: {CENARIO} | requisicoes: {total.num_requests} | "
          f"vazao media: {total.total_rps:.1f} req/s")
    print(f"Falhas: {falhas:.2f}% (limite 1%) -> {'ok' if ok_falhas else 'ACIMA'}")
    print(f"Tempo de resposta: media {total.avg_response_time:.0f} ms | "
          f"p95 {p95:.0f} ms (limite {limite}) -> {'ok' if ok_p95 else 'ACIMA'} | "
          f"maximo {total.max_response_time:.0f} ms")
    print(f"Resultado: {'APROVADO' if ok_falhas and ok_p95 else 'REPROVADO'}")
    print("==============================================\n")
    environment.process_exit_code = 0 if ok_falhas and ok_p95 else 1
