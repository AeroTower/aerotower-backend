import os

from dotenv import load_dotenv

# Le o .env da raiz quando ele existe, para o desenvolvimento local nao
# depender de exportar variavel na mao. Em producao (Render) o arquivo nao
# existe e as variaveis ja vem do ambiente — load_dotenv nao sobrescreve.
load_dotenv()

# ── MQTT ──────────────────────────────────
# Endereco e porta do broker: podem ser editados aqui, inclusive pelo editor
# do GitHub no navegador. Nao sao segredo. Se mudar o endereco, mude tambem
# em render.yaml (chave MQTT_BROKER) — ver DEPLOY.md.
BROKER    = os.getenv("MQTT_BROKER", "47d5de0ce14d4654a95021e273720719.s1.eu.hivemq.cloud")
PORT      = int(os.getenv("MQTT_PORT", "8883"))
# false so para testar com um broker local sem TLS (mosquitto na 1883).
MQTT_TLS  = os.getenv("MQTT_TLS", "true").strip().lower() != "false"

# Sem valor embutido de proposito: credencial com default no codigo vai
# parar no git, e foi o que aconteceu — a senha antiga esta no historico
# publico deste repositorio desde maio e precisa ser trocada no HiveMQ.
# Copie .env.example para .env e preencha.
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")

# ── Tópicos ───────────────────────────────
# Cada torre tem a sua "caixa": {MQTT_PREFIXO}/{torre_id}/sensores etc.
# (ver app/infrastructure/messaging/topicos.py).
MQTT_PREFIXO = os.getenv("MQTT_PREFIXO", "aerotower").strip("/")

# Topicos antigos, de antes de existir uma caixa por torre. Continuam
# assinados durante a transicao e tudo que chega neles conta como a
# TORRE_LEGADA — o firmware/simulador que ainda nao foi atualizado e o
# painel atual (rotas /dados, /motor/...) seguem funcionando.
TOPIC_SENSORES      = os.getenv("MQTT_TOPIC_SENSORES", "hidroponia/sensores")
TOPIC_MOTOR_COMANDO = os.getenv("MQTT_TOPIC_MOTOR_COMANDO", "hidroponia/motor/comando")
TOPIC_MOTOR_STATUS  = os.getenv("MQTT_TOPIC_MOTOR_STATUS", "hidroponia/motor/status")
TORRE_LEGADA        = os.getenv("TORRE_LEGADA", "AT-LEGADO").strip().upper()

# ── Login ─────────────────────────────────
# Client IDs OAuth do Google aceitos (web, Android, iOS), separados por
# virgula. Sao publicos — mas so tokens emitidos para eles passam.
GOOGLE_CLIENT_IDS = [
    c.strip() for c in os.getenv("GOOGLE_CLIENT_IDS", "").split(",") if c.strip()
]

# Assina o token de sessao proprio do back-end. Em producao TEM de vir do
# ambiente; sem ele, um valor aleatorio por processo faz todo mundo
# precisar logar de novo a cada reinicio (seguro, mas chato).
JWT_SEGREDO     = os.getenv("JWT_SEGREDO", "")
JWT_VALIDADE_DIAS = int(os.getenv("JWT_VALIDADE_DIAS", "30"))

# Liga POST /auth/dev, que aceita qualquer id sem Google. E o "token
# generico" para desenvolver o app enquanto o login real nao fica pronto.
# NUNCA deixe true em producao.
AUTH_MODO_DEV = os.getenv("AUTH_MODO_DEV", "false").strip().lower() in ("1", "true", "sim")

# Chave das rotas /admin (cadastro de torres na fabrica). Vazia = rotas
# desligadas.
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

# ── Banco de dados ────────────────────────
# Em Azure o valor deve vir via variavel de ambiente do App Service.
# Fallback apenas para desenvolvedor local.
_url = os.getenv("DATABASE_URL") or "postgresql://postgres:postgres@localhost:5432/hidroponia"
_url = _url.strip()

# O Render/Heroku entregam a URL do Postgres comecando com "postgres://",
# esquema que o SQLAlchemy 2.x nao reconhece mais.
if _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql://", 1)

DATABASE_URL = _url

# ── Fotos ─────────────────────────────────
DIRETORIO_ESTATICO = "static"
DIRETORIO_FOTOS    = "static/fotos"
URL_FOTOS          = "/static/fotos"
EXTENSOES_ACEITAS  = ["jpg", "jpeg", "png", "webp"]

# ── Log ───────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
