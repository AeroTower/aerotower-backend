# CT-DESEMP-02 · Teste de carga e de pico na API do Backend (Locust)

Simula **painéis do app abertos**: cada usuário virtual faz o que o app faz
(última leitura e status da bomba a cada 3 s; presença a cada 15 s).

| Cenário | O que faz | Duração | Passa se |
|---|---|---|---|
| `carga` | 50 painéis abertos ao mesmo tempo | 4 min | falhas ≤ 1% e p95 ≤ 1000 ms |
| `pico` | 10 painéis → salto para 200 em 5 s → volta a 10 | 4 min | falhas ≤ 1% e p95 ≤ 2000 ms |

No fim, o terminal imprime um bloco `CT-DESEMP-02` com **APROVADO** ou
**REPROVADO**. É esse bloco que vai para o relatório.

## Passo a passo (Windows, PowerShell)

**1. Marque o horário com o grupo.** Durante os 8 minutos o app e o auth
ficam lentos para todo mundo: os três serviços dividem o mesmo plano B1 na
Azure. Deixe a torre (ou o simulador) mandando dados, para o painel ter o
que mostrar.

**2. Instale o Locust** (uma vez), na pasta do repositório:
```powershell
py -m venv .venv-carga
.venv-carga\Scripts\activate
pip install locust
```

**3. Diga ao teste qual conta e qual torre usar.**
- *Jeito automático:* se o botão **Entrar sem Google** do app publicado
  funciona e essa conta (`demo`) já tem uma torre, não precisa fazer nada.
- *Jeito manual (sempre funciona):* abra https://app.aerotower.com.br, entre
  com o Google e abra o painel da torre. Aperte **F12** › aba **Rede**
  (Network) › clique num pedido para `aerotower-backend` › **Cabeçalhos** ›
  copie o valor de `Authorization` **sem** a palavra `Bearer`. Depois:
  ```powershell
  $env:AEROTOWER_TOKEN = "eyJ...cole aqui..."
  $env:AEROTOWER_TORRE = "AT-XXXXXXXXXXXX"   # o id que aparece no painel
  ```

**4. Abra o painel de métricas da Azure** (para o print do servidor):
portal.azure.com › `aerotower-backend` › **Métricas** › adicione
*CPU Percentage*, *Http 5xx* e *Response Time*, intervalo "Últimos 30 minutos".

**5. Rode a carga** (4 min):
```powershell
$env:CENARIO = "carga"
locust -f testes-carga\locustfile.py --headless --html carga.html --csv carga
```

**6. Rode o pico** (4 min), logo depois:
```powershell
$env:CENARIO = "pico"
locust -f testes-carga\locustfile.py --headless --html pico.html --csv pico
```

**7. Guarde as evidências:**
- print do bloco `CT-DESEMP-02` no terminal (um de cada cenário);
- abra `carga.html` e `pico.html` no navegador: print dos gráficos
  *Total Requests per Second* e *Response Times*;
- print das métricas da Azure no horário do teste.

Quer ver os gráficos ao vivo? Rode sem `--headless` e abra
http://localhost:8089. O cenário começa sozinho quando você clica em *Start*.
