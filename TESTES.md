# Testes do Backend

**Responsável pelos casos formais:** Fernão · **Cobertura:** 100% (meta da disciplina: 90%) · **159 testes**

| Tipo | Pasta | Testes | O que confere |
|---|---|---:|---|
| Unitário | `tests/unitarios/` | 97 | entidades, regras de alerta, casos de uso e adaptadores, com dublês no lugar de banco, MQTT, Redis e InfluxDB |
| Integração | `tests/integracao/` | 15 | rota HTTP → caso de uso → banco SQLite / MQTT falso |
| Funcional | `tests/funcionais/` | 15 | fluxos completos como o app usa (vincular, ler sensores, plantas, WebSocket) |
| Aceitação | `tests/aceitacao/` | 5 | critérios de aceite da história de usuário, em BDD (`monitorar_torre.feature`) |
| Desempenho | `tests/desempenho/` | 5 | carga (100 torres × 20 leituras), volume, pico de cliques, cache do catálogo |
| Segurança | `tests/seguranca/` | 22 | JWT forjado, torre de outra pessoa, upload malicioso, SQL injection, tópico MQTT forjado |

## Como rodar

**Terminal**
```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest --cov                 # todos, com cobertura (falha abaixo de 90%)
pytest -m seguranca          # só um tipo: unitario, integracao, funcional, aceitacao, desempenho, seguranca
pytest --cov --cov-report=html   # relatório navegável em htmlcov/index.html
```

**PyCharm**
1. *Settings › Tools › Python Integrated Tools › Testing › Default test runner*: **pytest**.
2. *Settings › Project › Python Interpreter*: instale `requirements.txt` e `requirements-dev.txt`.
3. Botão direito na pasta `tests` › **Run 'pytest in tests'**. Para a cobertura: **More Run/Debug › Run 'pytest in tests' with Coverage**. As linhas não testadas ficam vermelhas na margem do editor.
4. Para rodar só um tipo, use *Edit Configurations › Additional Arguments*: `-m seguranca`.

**GitHub**: o workflow `.github/workflows/testes.yml` roda em todo pull request. A aba *Actions* mostra a tabela por tipo, e *Artifacts › evidencias-testes-backend* traz o relatório de cobertura em HTML.

## Casos de teste formais (1 de cada tipo)

Plataforma de todos: Python 3.11, pytest 9, Ubuntu (GitHub Actions) e Windows (PyCharm).

### BE-UNI-01 · Unitário · Sensor fora da faixa gera alerta
| Campo | Valor |
|---|---|
| Cenário | O avaliador recebe uma leitura com um sensor fora dos limites padrão |
| Pré-requisitos | Nenhum (classe isolada, sem banco nem rede) |
| Passos | 1. Criar `LeituraSensores` com um único valor. 2. Chamar `AvaliadorDeAlertas().avaliar(leitura, Thresholds())` |
| Dados | pH 4,0 e 8,0 · EC 0,1 e 3,0 · água 31 °C · ambiente 40 °C · umidade 20% · nível 10% (8 execuções) |
| Esperado | Exatamente 1 alerta com o texto da faixa violada |
| Obtido | 8 de 8 execuções com 1 alerta correto |
| Status | ✅ Sucesso |
| Teste | `tests/unitarios/test_dominio.py::test_cada_sensor_fora_da_faixa_gera_alerta` |

### BE-INT-01 · Integração · Comando da bomba chega ao MQTT
| Campo | Valor |
|---|---|
| Cenário | O dono desliga a bomba pela API e a torre informa o novo status |
| Pré-requisitos | Torre vinculada ao usuário; broker MQTT substituído por dublê |
| Passos | 1. `POST /torres/{id}/motor/desligar` com token do dono. 2. Torre publica em `aerotower/{id}/motor/status`. 3. `GET /torres/{id}/motor/status` |
| Dados | `{"ligado": false, "ciclo_ativo": false}` |
| Esperado | 200; mensagem `{"acao": "desligar"}` publicada em `aerotower/{id}/motor/comando`; status com `ligado = false` |
| Obtido | Conforme esperado |
| Status | ✅ Sucesso |
| Teste | `tests/integracao/test_api.py::test_desligar_e_status_do_motor` |

### BE-FUN-01 · Funcional · Fluxo completo e isolamento entre usuários
| Campo | Valor |
|---|---|
| Cenário | Torre é cadastrada na fábrica, vinculada à Maria, publica dados e recebe comando |
| Pré-requisitos | Backend rodando com banco limpo |
| Passos | 1. Worker do auth cadastra e vincula a torre. 2. Maria lista as torres. 3. João tenta ler e comandar. 4. Torre publica sensores, status e info. 5. Maria programa um ciclo |
| Dados | pH 7,4 · TDS 600 · nível 20% · ciclo 10/50 min |
| Esperado | Maria vê 1 torre (kit pro) e os alertas de pH e nível; João recebe 404 e nada é publicado; comando vai para o tópico da torre |
| Obtido | Conforme esperado |
| Status | ✅ Sucesso |
| Teste | `tests/funcionais/test_fluxo_torres.py::test_fluxo_e_isolamento` |

### BE-ACE-01 · Aceitação (BDD) · Leitura fora da faixa vira alerta no painel
| Campo | Valor |
|---|---|
| Cenário | *Dado* que a Maria tem uma torre do kit "pro"; *quando* a torre publica pH 7,4 e nível 20; *então* o painel mostra "pH acima" e "Nível de água baixo" |
| Pré-requisitos | História de usuário "Monitorar e controlar a minha torre pelo app" |
| Passos | Executados pelos passos em português de `monitorar_torre.feature` |
| Dados | pH 7,4 · nível 20% |
| Esperado | Os dois alertas no `GET /torres/{id}/dados` |
| Obtido | Os dois alertas presentes (e os outros 4 cenários da história também passaram) |
| Status | ✅ Sucesso |
| Teste | `tests/aceitacao/monitorar_torre.feature` |

### BE-DES-01 · Desempenho (carga) · 100 torres publicando
| Campo | Valor |
|---|---|
| Cenário | 100 torres enviam 20 leituras cada pelo MQTT |
| Pré-requisitos | 100 torres cadastradas e vinculadas |
| Passos | 1. Publicar 2.000 mensagens em sequência. 2. Medir o tempo total. 3. Conferir a última leitura de cada torre |
| Dados | `{"ph": 6.0, "nivelAgua": 50}` |
| Esperado | Menos de 10 s no total (limite folgado) e nenhuma leitura perdida |
| Obtido | 0,9 s (≈ 2.200 mensagens/s); 100 de 100 torres com leitura |
| Status | ✅ Sucesso |
| Teste | `tests/desempenho/test_desempenho.py::test_carga_mqtt_100_torres_publicando` |

### BE-SEG-01 · Segurança · Token JWT sem assinatura
| Campo | Valor |
|---|---|
| Cenário | Atacante monta um token com `alg: none` para se passar pela Maria |
| Pré-requisitos | Backend com `JWT_SEGREDO` configurado |
| Passos | 1. Gerar token sem assinatura com `sub = maria`. 2. `GET /torres` com esse token |
| Dados | Cabeçalho `{"alg": "none"}`, emissor e audiência corretos |
| Esperado | 401 com `WWW-Authenticate: Bearer`, sem nenhum dado |
| Obtido | 401 |
| Status | ✅ Sucesso |
| Teste | `tests/seguranca/test_seguranca.py::test_token_sem_assinatura_e_recusado` |

## Testes individuais que acham defeitos (Fernão)

Estes testes afirmam o comportamento **correto**. Em 24/11/2026 todos
falharam e cada falha mostrou um defeito real. Na refatoração seguinte (ciclo
do TDD: teste falhando, correção mínima, refatoração) os defeitos de código
foram corrigidos e os testes saíram da marca `defeito`: agora rodam na suíte
normal e protegem contra a volta do problema. O passo "Testes que acham
defeitos" continua no CI para os próximos testes desse tipo.

| ID | Tipo | Defeito que o teste mostrou | Correção | Situação |
|---|---|---|---|---|
| CT-UNIT-02 | Unitário | Limites de alerta impossíveis eram aceitos (pH mín. 8 > máx. 6, umidade 150%) | `Thresholds` valida a faixa física e mínimo < máximo; a API responde 422 | ✅ Corrigido |
| CT-INT-02 | Integração | Leitura com `NaN` pelo MQTT derrubava o painel (HTTP 500); `Infinity` virava alerta "inf" | Valores não finitos são descartados na chegada, com aviso | ✅ Corrigido |
| CT-FUNC-02 | Funcional | Comando para torre offline respondia "Ciclo iniciado" e o comando se perdia | Torre que avisou "offline" responde 409 (ciclo e desligar) | ✅ Corrigido |
| CT-ACEIT-02 | Aceitação (BDD) | Sonda de pH solta (-3,2 / 21,4) virava "pH abaixo/acima" | Leitura fora da faixa física vira "Sensor de pH com leitura inválida (confira a sonda)" | ✅ Corrigido |
| CT-DESEMP-02 | Desempenho | API lenta com 50 painéis e fora do ar num pico de 200 (`testes-carga/`, Locust) | Depende de infraestrutura: separar o MQTT do processo da API e escalar na Azure | ⏳ Aberto |
| CT-SEG-02 | Segurança | Sem login: lista de e-mails da loja e rotas legado que comandavam a bomba | `/eventos/interesses` e exportações pedem `X-Admin-Key` (`ADMIN_API_KEY`); rotas legado de comando pedem o token do dono da `TORRE_LEGADA` | ✅ Corrigido |
