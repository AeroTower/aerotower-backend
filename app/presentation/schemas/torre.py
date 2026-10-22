from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.domain.entities.kit import Kit


class TorreResponse(BaseModel):
    id:              str
    apelido:         Optional[str] = None
    kit:             Kit
    # O app usa esta lista para decidir quais cards mostrar:
    # bomba, nivel, ph, tds, clima.
    capacidades:     List[str]
    online:          Optional[bool] = None
    firmware:        Optional[str] = None
    ultimaLeituraEm: Optional[datetime] = None
    ativadaEm:       Optional[datetime] = None
