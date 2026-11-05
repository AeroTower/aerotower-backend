from dataclasses import dataclass
from typing import Optional


@dataclass
class Planta:
    nome: str
    tipo: str
    data_plantio: str
    foto_url: Optional[str] = None
    id: Optional[int] = None
    # A planta e de uma pessoa NUMA torre: se a torre muda de dono, quem
    # chega nao ve as plantas de quem saiu.
    torre_id: Optional[str] = None
    usuario_id: Optional[str] = None
