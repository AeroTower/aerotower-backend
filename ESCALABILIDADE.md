# Várias torres: como funciona e como implantar

## A ideia em três partes

1. **Cada torre tem a sua caixa no broker.** Um broker só (HiveMQ), um
   prefixo de tópico por torre: `aerotower/<torre_id>/...`. O `torre_id`
   é `AT-` + MAC do ESP32, lido no boot. O back-end assina
   `aerotower/+/sensores` e tira o id do **tópico**, nunca do payload.
2. **Cada pessoa tem um nome.** Login com Google. O back-end guarda o `sub`
   da conta (não o e-mail) e devolve um token próprio de 30 dias.
3. **O código do adesivo liga os dois.** Na fábrica, o servidor gera um
   código aleatório de uso único para cada torre. A pessoa digita o código
   no app, o servidor grava "pessoa ↔ torre" e queima o código. O banco
   guarda só o hash.

O celular nunca fala com o broker. Ele fala com o back-end, que confere se
a torre é da pessoa antes de mandar qualquer comando.

## Kits

| Kit | Capacidades | O app mostra |
|---|---|---|
| `basico` | `bomba` | controle da bomba e um aviso de "sem sensores" |
| `completo` | `bomba`, `nivel` | + reservatório |
| `pro` | `bomba`, `nivel`, `ph`, `tds`, `clima` | + pH, TDS, temperatura e o botão da IA |

O kit é gravado no cadastro de fábrica e volta em `capacidades` em toda
resposta de torre. O back-end também descarta da leitura os campos de
sensores que o kit não tem.

## Contrato para o app (login Google)

```
POST /auth/google   {"idToken": "<GoogleSignInAuthentication.idToken>"}
POST /auth/dev      {"id": "qualquer-coisa"}        # só com AUTH_MODO_DEV=true
  -> {"token": "...", "usuario": {"id", "email", "nome"}}
```

Daqui em diante, `Authorization: Bearer <token>` em tudo:

```
GET  /auth/me
GET  /torres                         -> [{id, apelido, kit, capacidades, online, firmware, ...}]
POST /torres/ativar                  {"codigo": "K9X2-7QHM", "apelido": "Varanda"}
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

O `idToken` precisa ter sido emitido para um dos client IDs em
`GOOGLE_CLIENT_IDS` (web, Android e iOS, separados por vírgula). No
`google_sign_in` para Android, o `serverClientId` deve ser o client ID **web**
— é esse que vai como `aud` no token.

## Fábrica

```
export AEROTOWER_API=https://<backend>   ADMIN_API_KEY=<chave>
python scripts/provisionar_torre.py --kit pro --porta COM5
```

Lê o `TORRE_ID` da placa pela USB, cadastra e gera `etiquetas/<id>.png`
com QR e código. Adesivo perdido ou revenda: `--novo-codigo`.

Simular torres sem hardware (cadastre os ids antes):

```
python scripts/simulador_torres.py --torre AT-5130AA000001:pro --torre AT-5130AA000002:basico
```

## Variáveis de ambiente novas

| Variável | Para quê |
|---|---|
| `JWT_SEGREDO` | assina o token de sessão. Obrigatória em produção. |
| `GOOGLE_CLIENT_IDS` | client IDs aceitos no login Google |
| `AUTH_MODO_DEV` | `true` libera `/auth/dev`. Desligar quando o Google estiver pronto. |
| `ADMIN_API_KEY` | protege `/admin/*` (script de fábrica) |
| `TORRE_LEGADA` | id que recebe os tópicos `hidroponia/*` e as rotas antigas (padrão `AT-LEGADO`) |
| `MQTT_PREFIXO` | padrão `aerotower` |
| `MQTT_TLS` | `false` só para testar com broker local |

As tabelas `usuarios` e `torres` são criadas sozinhas no primeiro start.

## Ordem de implantação (sem quebrar a demonstração)

1. **Back-end.** Publique esta branch e configure as variáveis acima, com
   `AUTH_MODO_DEV=true`. Nada antigo para: os tópicos `hidroponia/*` e as
   rotas `/dados`, `/motor/*`, `/thresholds` continuam valendo para a
   `TORRE_LEGADA`.
2. **Protótipo.** Grave o firmware v2 e rode o script de fábrica.
3. **App.** Publique o app novo e ative a torre com o código.
4. **Google.** Quando o login estiver pronto, preencha `GOOGLE_CLIENT_IDS`
   e troque `AUTH_MODO_DEV` para `false`.
5. **Limpeza.** Apague `routers/sensores.py`, `motor.py`, `thresholds.py`
   e as assinaturas `hidroponia/*` em `messaging/topicos.py`.

## O que ainda não escala (próximos passos)

- **Plantas** continuam globais: todo usuário vê as mesmas. Falta uma
  coluna `torre_id` na tabela `plantas` (precisa de migração, o
  `create_all` não altera tabela existente).
- **Thresholds e última leitura** ficam em memória, por torre. Somem num
  restart; o próximo passo é levá-los para o banco.
- **Um processo só.** Continua valendo o aviso do `startup.sh`: o consumidor
  MQTT vive dentro da API. Para mais de uma instância, separe o consumidor
  e coloque o WebSocket atrás de um broker compartilhado.
- **Credencial por torre no broker.** No HiveMQ Serverless a permissão vale
  para todos os tópicos. No plano Starter, uma regra
  `aerotower/${mqtt-username}/#` com usuário = id da torre impede que uma
  torre (ou quem extrair a senha dela) mexa nas outras.
- **Certificado TLS no ESP32** (`setCACert` no lugar de `setInsecure`).
