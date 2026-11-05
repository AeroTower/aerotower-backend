# Várias torres: como o Backend se encaixa

## Quem faz o quê

| Serviço | Repositório | Responsabilidade |
|---|---|---|
| **Backend** (este) | `aerotower-backend` | Telemetria MQTT, alertas, comandos da bomba, plantas, WebSocket |
| **Auth** (Serviço A + B) | `aerotower-auth` | Login Google, token de sessão, vínculo pessoa ↔ torre, cadastro de fábrica, eventos RabbitMQ |
| **Torre** | `aerotower-firmware` | ESP32 publicando em `aerotower/<id>/...`; simulador em `simulador/` |

```
ESP32 ──MQTT──▶ HiveMQ ──▶ Backend ◀──PUT /internal/torres/{id}── worker ◀── RabbitMQ ◀── API de auth
                              ▲                                                            ▲
                              └──────────── App Flutter (mesmo token nos dois) ────────────┘
```

O Backend **não faz login**. Ele confere o token emitido pelo serviço de
auth (mesmo `JWT_SEGREDO`, emissor `aerotower-auth`, audiência `aerotower`)
e sabe de quem é cada torre pela cópia local alimentada pelos eventos.

## Tópicos MQTT

```
aerotower/<torre_id>/sensores        torre -> servidor
aerotower/<torre_id>/motor/status    torre -> servidor (retido)
aerotower/<torre_id>/motor/comando   servidor -> torre
aerotower/<torre_id>/status          online/offline (LWT, retido)
aerotower/<torre_id>/info            firmware, kit, sensores (retido)
```

O id da torre sai **do tópico**, nunca do payload.

## Kits

| Kit | Capacidades | O app mostra |
|---|---|---|
| `basico` | `bomba` | controle da bomba e um aviso de "sem sensores" |
| `completo` | `bomba`, `nivel` | + reservatório |
| `pro` | `bomba`, `nivel`, `ph`, `tds`, `clima` | + pH, TDS, temperatura e o botão da IA |

O Backend descarta da leitura os campos de sensores que o kit não tem.

## Rotas

Todas com `Authorization: Bearer <token do serviço de auth>`:

```
GET  /torres                         -> [{id, apelido, kit, capacidades, online, firmware, ...}]
GET  /torres/{id}
GET  /torres/{id}/dados              -> {torreId, capacidades, dados, alertas, recebidoEm}
GET  /torres/{id}/alertas
GET|POST /torres/{id}/thresholds
POST /torres/{id}/motor/ciclo        {"minutos_ligado": 15, "minutos_desligado": 45}
POST /torres/{id}/motor/desligar
GET  /torres/{id}/motor/status
WS   /ws/sensores?token=<token>[&torre=<id>]
```

Torre de outra pessoa responde 404, igual a uma que não existe.

Interna (só o worker do auth, `X-Service-Key`):

```
PUT /internal/torres/{id}   {"kit", "donoId", "apelido", "versao"}
```

Idempotente: evento repetido ou atrasado (versão menor ou igual à
guardada) é ignorado.

**Consistência eventual:** entre o `POST /torre/vincular` no auth e a torre
aparecer aqui passa o tempo de o worker entregar o evento (milissegundos,
ou alguns segundos se o Backend estiver acordando). O app tenta de novo
algumas vezes antes de desistir.

## Variáveis de ambiente

| Variável | Para quê |
|---|---|
| `JWT_SEGREDO` | confere o token. **Mesmo valor do auth** |
| `SERVICO_API_KEY` | protege `/internal/*`. **Mesmo valor do auth** |
| `TORRE_LEGADA` | id que recebe os tópicos `hidroponia/*` e as rotas antigas (padrão `AT-LEGADO`) |
| `MQTT_PREFIXO` | padrão `aerotower` |
| `MQTT_TLS` | `false` só para testar com broker local |

A tabela `torres` é criada sozinha no primeiro start. Banco novo? Chame
`POST /admin/sincronizar` no serviço de auth para reenviar todas.

## Plantas

Cada planta é de uma pessoa **numa** torre (`torre_id` + `usuario_id`), só
pelas rotas `/torres/{id}/plantas`. Se a torre muda de dono, quem chega não vê
as plantas de quem saiu; se o dono antigo voltar, as dele continuam lá. A
rota antiga `/plantas` (sem login) saiu. As colunas novas são criadas pela
`migracoes.py` no start.

## O que ainda não escala (próximos passos)

- **Um processo só.** O consumidor MQTT vive dentro da API (ver `startup.sh`).
- **Credencial MQTT por torre** (HiveMQ Starter, regra
  `aerotower/${mqtt-username}/#`). O worker do auth é o lugar natural para
  criá-la ao receber `torre.cadastrada`.
- **Certificado TLS no ESP32** (`setCACert` no lugar de `setInsecure`).
