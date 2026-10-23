from typing import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.use_cases.atualizar_thresholds import AtualizarThresholds
from app.application.use_cases.buscar_planta import BuscarPlanta
from app.application.use_cases.criar_planta import CriarPlanta
from app.application.use_cases.deletar_planta import DeletarPlanta
from app.application.use_cases.desligar_motor import DesligarMotor
from app.application.use_cases.iniciar_ciclo_motor import IniciarCicloMotor
from app.application.use_cases.listar_plantas import ListarPlantas
from app.application.use_cases.obter_alertas import ObterAlertas
from app.application.use_cases.obter_resumo_validacao import (
    ExportarEventos,
    ListarInteresses,
    ObterResumoValidacao,
)
from app.application.use_cases.obter_status_motor import ObterStatusMotor
from app.application.use_cases.obter_thresholds import ObterThresholds
from app.application.use_cases.obter_ultima_leitura import ObterUltimaLeitura
from app.application.use_cases.processar_leitura import ProcessarLeitura
from app.application.use_cases.processar_status_motor import ProcessarStatusMotor
from app.application.use_cases.registrar_evento import RegistrarEvento
from app.application.use_cases.registrar_interesse import RegistrarInteresse
from app.domain.services.avaliador_alertas import AvaliadorDeAlertas
from app.domain.services.validador_evento import ValidadorDeEvento
from app.infrastructure.messaging.mqtt_client import criar_cliente
from app.infrastructure.messaging.mqtt_publicador import MqttPublicador
from app.infrastructure.messaging.mqtt_subscriber import MqttSubscriber
from app.infrastructure.notifications.websocket_notificador import WebSocketNotificador
from app.infrastructure.persistence.database import get_session
from app.infrastructure.persistence.sqlalchemy_evento_repository import (
    SqlAlchemyEventoRepository,
)
from app.infrastructure.persistence.sqlalchemy_planta_repository import (
    SqlAlchemyPlantaRepository,
)
from app.infrastructure.state.estado_memoria import EstadoEmMemoria
from app.infrastructure.storage.filesystem_foto_storage import FilesystemFotoStorage
from app.core.config import REDIS_URL
from app.infrastructure.state.estado_redis import EstadoRedis

class Container:
    def __init__(self):
        self.mqtt_client   = criar_cliente()
        self.estado        = EstadoRedis(REDIS_URL) if REDIS_URL else EstadoEmMemoria()
        self.notificador   = WebSocketNotificador()
        self.armazenamento = FilesystemFotoStorage()
        self.avaliador     = AvaliadorDeAlertas()
        self.validador_evento = ValidadorDeEvento()
        self.publicador    = MqttPublicador(self.mqtt_client)

        self.processar_leitura = ProcessarLeitura(
            self.estado, self.avaliador, self.notificador
        )
        self.processar_status_motor = ProcessarStatusMotor(self.estado, self.notificador)

        self.subscriber = MqttSubscriber(
            self.mqtt_client, self.processar_leitura, self.processar_status_motor
        )

        self.obter_ultima_leitura = ObterUltimaLeitura(self.estado)
        self.obter_alertas        = ObterAlertas(self.estado)
        self.obter_thresholds     = ObterThresholds(self.estado)
        self.atualizar_thresholds = AtualizarThresholds(self.estado)
        self.iniciar_ciclo_motor  = IniciarCicloMotor(self.publicador)
        self.desligar_motor       = DesligarMotor(self.publicador)
        self.obter_status_motor   = ObterStatusMotor(self.estado)


container = Container()


def get_notificador() -> WebSocketNotificador:
    return container.notificador


def get_obter_ultima_leitura() -> ObterUltimaLeitura:
    return container.obter_ultima_leitura


def get_obter_alertas() -> ObterAlertas:
    return container.obter_alertas


def get_obter_thresholds() -> ObterThresholds:
    return container.obter_thresholds


def get_atualizar_thresholds() -> AtualizarThresholds:
    return container.atualizar_thresholds


def get_iniciar_ciclo_motor() -> IniciarCicloMotor:
    return container.iniciar_ciclo_motor


def get_desligar_motor() -> DesligarMotor:
    return container.desligar_motor


def get_obter_status_motor() -> ObterStatusMotor:
    return container.obter_status_motor


def get_planta_repository(
    session: Session = Depends(get_session),
) -> Iterator[SqlAlchemyPlantaRepository]:
    yield SqlAlchemyPlantaRepository(session)


def get_listar_plantas(
    repositorio: SqlAlchemyPlantaRepository = Depends(get_planta_repository),
) -> ListarPlantas:
    return ListarPlantas(repositorio)


def get_buscar_planta(
    repositorio: SqlAlchemyPlantaRepository = Depends(get_planta_repository),
) -> BuscarPlanta:
    return BuscarPlanta(repositorio)


def get_criar_planta(
    repositorio: SqlAlchemyPlantaRepository = Depends(get_planta_repository),
) -> CriarPlanta:
    return CriarPlanta(repositorio, container.armazenamento)


def get_deletar_planta(
    repositorio: SqlAlchemyPlantaRepository = Depends(get_planta_repository),
) -> DeletarPlanta:
    return DeletarPlanta(repositorio, container.armazenamento)


def get_evento_repository(
    session: Session = Depends(get_session),
) -> Iterator[SqlAlchemyEventoRepository]:
    yield SqlAlchemyEventoRepository(session)


def get_registrar_evento(
    repositorio: SqlAlchemyEventoRepository = Depends(get_evento_repository),
) -> RegistrarEvento:
    return RegistrarEvento(repositorio, container.validador_evento)


def get_registrar_interesse(
    repositorio: SqlAlchemyEventoRepository = Depends(get_evento_repository),
) -> RegistrarInteresse:
    return RegistrarInteresse(repositorio, container.validador_evento)


def get_obter_resumo_validacao(
    repositorio: SqlAlchemyEventoRepository = Depends(get_evento_repository),
) -> ObterResumoValidacao:
    return ObterResumoValidacao(repositorio)


def get_listar_interesses(
    repositorio: SqlAlchemyEventoRepository = Depends(get_evento_repository),
) -> ListarInteresses:
    return ListarInteresses(repositorio)


def get_exportar_eventos(
    repositorio: SqlAlchemyEventoRepository = Depends(get_evento_repository),
) -> ExportarEventos:
    return ExportarEventos(repositorio)
