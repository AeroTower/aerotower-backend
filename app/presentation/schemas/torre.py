from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.domain.entities.kit import Kit


class AtivarTorreRequest(BaseModel):
    codigo:  str = Field(..., description="Código do adesivo, ex.: K9X2-7QHM (hífen e maiúsculas opcionais)")
    apelido: Optional[str] = Field(None, max_length=40, description="Nome que aparece no app, ex.: Varanda")


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


class CadastrarTorreRequest(BaseModel):
    torreId: str = Field(..., description="AT-<MAC>, impresso pelo ESP32 no monitor serial")
    kit:     Kit


class CodigoAtivacaoResponse(BaseModel):
    torreId:        str
    kit:            Kit
    codigoAtivacao: str = Field(..., description="Vai para o adesivo. Só aparece nesta resposta.")


class TorreAdminResponse(BaseModel):
    id:        str
    kit:       Kit
    ativada:   bool
    donoId:    Optional[str] = None
    criadaEm:  Optional[datetime] = None
    ativadaEm: Optional[datetime] = None
