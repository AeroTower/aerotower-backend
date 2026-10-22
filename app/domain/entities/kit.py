from enum import Enum
from typing import Dict, Iterable, List, Optional


class Kit(str, Enum):
    """Linha de produtos. O kit decide o que a torre mede e o que o app mostra."""

    BASICO   = "basico"
    COMPLETO = "completo"
    PRO      = "pro"


# Toda torre tem bomba com ciclos. O resto depende do kit vendido.
CAPACIDADES_POR_KIT: Dict[Kit, List[str]] = {
    Kit.BASICO:   ["bomba"],
    Kit.COMPLETO: ["bomba", "nivel"],
    Kit.PRO:      ["bomba", "nivel", "ph", "tds", "clima"],
}

# Campos da leitura que pertencem a cada capacidade. Inclui os nomes antigos
# do firmware (temperatura, umidade) para torres que ainda nao foram
# regravadas. Campo que nao aparece aqui (motor, ciclo_ativo...) e comum a
# todos os kits e nunca e filtrado.
CAMPOS_POR_CAPACIDADE: Dict[str, List[str]] = {
    "nivel": [
        "nivelAgua", "tanque_litros", "tanque_nivel_cm",
        "tanque_distancia_cm", "tanque_status",
    ],
    "ph":    ["ph", "ph_status"],
    "tds":   ["tds", "ec", "tds_status"],
    "clima": [
        "temperaturaAmbiente", "umidadeRelativa", "ambiente",
        "temperatura", "umidade",
    ],
}


def capacidades_do_kit(kit: Kit) -> List[str]:
    return list(CAPACIDADES_POR_KIT[kit])


def filtrar_por_capacidades(
    dados: Dict, capacidades: Optional[Iterable[str]]
) -> Dict:
    """Remove da leitura os campos de sensores que o kit nao tem.

    Um pino analogico sem sonda le ruido; se uma torre basica publicar "ph",
    esse numero nao pode virar alerta nem aparecer no painel. `None` em
    `capacidades` significa torre desconhecida: nada e filtrado.
    """
    if capacidades is None:
        return dict(dados)
    permitidas = set(capacidades)
    proibidos = {
        campo
        for capacidade, campos in CAMPOS_POR_CAPACIDADE.items()
        if capacidade not in permitidas
        for campo in campos
    }
    return {chave: valor for chave, valor in dados.items() if chave not in proibidos}
