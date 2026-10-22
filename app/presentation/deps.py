import secrets
from typing import Iterator, Optional

from fastapi import Depends, Header, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.application.use_cases.atualizar_thresholds import AtualizarThresholds
from app.application.use_cases.buscar_planta import BuscarPlanta
from app.application.use_cases.consultar_torres import ListarMinhasTorres, ObterTorreDoUsuario
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
from app.application.use_cases.processar_presenca import ProcessarPresenca
from app.application.use_cases.processar_status_motor import ProcessarStatusMotor
from app.application.use_cases.sincronizar_torre import SincronizarTorre
from app.application.use_cases.registrar_evento import RegistrarEvento
from app.application.use_cases.registrar_interesse import RegistrarInteresse
from app.core.config import JWT_SEGREDO, SERVICO_API_KEY
from app.domain.entities.torre import Torre
from app.domain.exceptions import AcessoNegado, NaoAutenticado
from app.domain.services.avaliador_alertas import AvaliadorDeAlertas
from app.domain.services.validador_evento import ValidadorDeEvento
from app.infrastructure.auth.jwt_validador import JwtValidador
from app.infrastructure.messaging.mqtt_client import criar_cliente
from app.infrastructure.messaging.mqtt_publicador import MqttPublicador
from app.infrastructure.messaging.mqtt_subscriber import MqttSubscriber
from app.infrastructure.notifications.websocket_notificador import WebSocketNotificador
from app.infrastructure.persistence.catalogo_torres import CatalogoSqlAlchemy
from app.infrastructure.persistence.database import get_session
from app.infrastructure.persistence.historico_influx import HistoricoInflux
from app.infrastructure.persistence.sqlalchemy_evento_repository import (
    SqlAlchemyEventoRepository,
)
from app.infrastructure.persistence.sqlalchemy_planta_repository import (
    SqlAlchemyPlantaRepository,
)
from app.infrastructure.persistence.sqlalchemy_torre_repository import (
    SqlAlchemyTorreRepository,
)
from app.infrastructure.state.estado_memoria import EstadoEmMemoria
from app.infrastructure.storage.filesystem_foto_storage import FilesystemFotoStorage


class Container:
    def __init__(self):
        self.mqtt_client   = criar_cliente()
        self.estado        = EstadoEmMemoria()
        self.notificador   = WebSocketNotificador()
        self.armazenamento = FilesystemFotoStorage()
        self.avaliador     = AvaliadorDeAlertas()
        self.validador_evento = ValidadorDeEvento()
        self.publicador    = MqttPublicador(self.mqtt_client)
        self.catalogo      = CatalogoSqlAlchemy()
        self.historico     = HistoricoInflux()

        self.validador_sessao = JwtValidador(JWT_SEGREDO)

        self.processar_leitura = ProcessarLeitura(
            self.estado, self.avaliador, self.notificador, self.catalogo, self.historico
        )
        self.processar_status_motor = ProcessarStatusMotor(self.estado, self.notificador)
        self.processar_presenca     = ProcessarPresenca(self.estado, self.notificador)

        self.subscriber = MqttSubscriber(
            self.mqtt_client,
            self.processar_leitura,
            self.processar_status_motor,
            self.processar_presenca,
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


# =============================================
# Sessao (token do servico de auth) e acesso as torres
# =============================================

def get_torre_repository(
    session: Session = Depends(get_session),
) -> Iterator[SqlAlchemyTorreRepository]:
    yield SqlAlchemyTorreRepository(session)


# HTTPBearer (e nao um Header "authorization") faz o /docs mostrar o botao
# Authorize: o Swagger ignora parametro de cabecalho chamado Authorization.
_bearer = HTTPBearer(auto_error=False, description="Token do serviço de autenticação (aerotower-auth)")


def usuario_do_token(token: str) -> str:
    """Tambem usado pelo WebSocket, que recebe o token na query string."""
    return container.validador_sessao.validar(token)


def get_usuario_id(
    credenciais: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> str:
    if credenciais is None:
        raise NaoAutenticado("Envie o header Authorization: Bearer <token>.")
    return usuario_do_token(credenciais.credentials.strip())


def get_torre_do_usuario(
    torre_id: str = Path(..., description="Id da torre, ex.: AT-24DCC3A1B2C4"),
    usuario_id: str = Depends(get_usuario_id),
    torres: SqlAlchemyTorreRepository = Depends(get_torre_repository),
) -> Torre:
    """Toda rota /torres/{torre_id}/... passa por aqui: so o dono entra."""
    return ObterTorreDoUsuario(torres).executar(usuario_id, torre_id.upper())


def get_listar_minhas_torres(
    torres: SqlAlchemyTorreRepository = Depends(get_torre_repository),
) -> ListarMinhasTorres:
    return ListarMinhasTorres(torres)


# =============================================
# Rota interna (worker do servico de auth)
# =============================================

def exigir_servico(x_service_key: Optional[str] = Header(default=None)) -> None:
    if not SERVICO_API_KEY:
        raise AcessoNegado("Rota interna desligada (SERVICO_API_KEY não definida).")
    if not x_service_key or not secrets.compare_digest(x_service_key, SERVICO_API_KEY):
        raise AcessoNegado("Chave de serviço inválida.")


def get_sincronizar_torre(
    torres: SqlAlchemyTorreRepository = Depends(get_torre_repository),
) -> SincronizarTorre:
    return SincronizarTorre(torres)
