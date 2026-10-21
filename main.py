import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import DATABASE_URL, DIRETORIO_ESTATICO, DIRETORIO_FOTOS
from app.core.logging_config import configurar_logging
from app.infrastructure.messaging.mqtt_client import conectar, desconectar
from app.infrastructure.persistence import models  # noqa: F401
from app.infrastructure.persistence.database import Base, engine
from app.presentation.deps import container
from app.presentation.exception_handlers import registrar_handlers
from app.presentation.middleware.cors import registrar_cors
from app.presentation.routers import (
    admin,
    auth,
    eventos,
    geral,
    motor,
    plantas,
    sensores,
    thresholds,
    torres,
    websocket,
)

configurar_logging()

os.makedirs(DIRETORIO_FOTOS, exist_ok=True)

# Com DATABASE_URL apontando para fora do wwwroot (ex.: no Azure,
# sqlite:////home/data/plantas.db), a pasta precisa existir antes de o
# SQLAlchemy abrir o arquivo — ele não a cria sozinho.
_db = DATABASE_URL
if _db.startswith("sqlite:"):
    _caminho = _db.split("sqlite:///")[-1]
    _pasta = os.path.dirname(_caminho)
    if _pasta:
        os.makedirs(_pasta, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    container.notificador.definir_event_loop(asyncio.get_running_loop())

    Base.metadata.create_all(bind=engine)

    container.subscriber.registrar()
    conectar(container.mqtt_client)

    yield

    desconectar(container.mqtt_client)


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory=DIRETORIO_ESTATICO), name="static")

registrar_cors(app)
registrar_handlers(app)

app.include_router(geral.router)
app.include_router(auth.router)
app.include_router(torres.router)
app.include_router(admin.router)
app.include_router(sensores.router)
app.include_router(thresholds.router)
app.include_router(motor.router)
app.include_router(plantas.router)
app.include_router(eventos.router)
app.include_router(websocket.router)
