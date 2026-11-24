import logging
import math
from datetime import datetime
from typing import Any, Dict, Optional

from app.application.ports.catalogo_torres import CatalogoDeTorres
from app.application.ports.estado_monitoramento import EstadoDeMonitoramento
from app.application.ports.historico_leituras import HistoricoDeLeituras
from app.application.ports.notificador import Notificador
from app.domain.entities.kit import filtrar_por_capacidades
from app.domain.entities.leitura import LeituraAvaliada, LeituraSensores
from app.domain.services.avaliador_alertas import AvaliadorDeAlertas

logger = logging.getLogger(__name__)


class ProcessarLeitura:
    def __init__(
        self,
        estado: EstadoDeMonitoramento,
        avaliador: AvaliadorDeAlertas,
        notificador: Notificador,
        catalogo: CatalogoDeTorres,
        historico: Optional[HistoricoDeLeituras] = None,
    ):
        self._estado = estado
        self._avaliador = avaliador
        self._notificador = notificador
        self._catalogo = catalogo
        self._historico = historico

    def executar(self, torre_id: str, dados: Dict[str, Any]) -> LeituraAvaliada:
        # So o que o kit tem: sensor ausente nao vira numero nem alerta.
        filtrados = filtrar_por_capacidades(dados, self._catalogo.capacidades(torre_id))
        filtrados, descartados = _sem_valores_nao_finitos(filtrados)
        if descartados:
            logger.warning("Leitura com valor nao numerico [%s]: %s descartado(s)", torre_id, descartados)

        leitura = LeituraSensores(bruto=filtrados, recebido_em=datetime.now())
        alertas = [f"Leitura inválida do sensor descartada: {campo}" for campo in descartados]
        alertas += self._avaliador.avaliar(leitura, self._estado.thresholds(torre_id))
        avaliada = LeituraAvaliada(leitura=leitura, alertas=alertas)

        self._estado.salvar_leitura(torre_id, avaliada)
        logger.info("Sensores [%s]: %s", torre_id, filtrados)

        if self._historico is not None:
            self._historico.registrar(torre_id, filtrados)

        self._notificador.notificar(torre_id, {
            "torreId":    torre_id,
            "dados":      leitura.bruto,
            "alertas":    alertas,
            "recebidoEm": leitura.recebido_em.isoformat(),
        })
        return avaliada


def _sem_valores_nao_finitos(dados: Dict[str, Any]):
    """NaN e infinito (o json do Python aceita os dois) nao viram JSON nem alerta."""
    descartados = [chave for chave, valor in dados.items()
                   if isinstance(valor, float) and not math.isfinite(valor)]
    limpos = {chave: valor for chave, valor in dados.items() if chave not in descartados}
    return limpos, descartados
