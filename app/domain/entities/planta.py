from dataclasses import dataclass
from typing import Optional


@dataclass
class Planta:
    nome: str
    tipo: str
    data_plantio: str
    foto_url: Optional[str] = None
    id: Optional[int] = None
    # Torre dona da planta. None = planta antiga, de antes de existirem
    # varias torres (so aparece nas rotas legadas /plantas).
    torre_id: Optional[str] = None
