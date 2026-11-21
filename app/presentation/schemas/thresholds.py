from typing import Optional

from pydantic import BaseModel


class ThresholdsUpdate(BaseModel):
    phMin:                  Optional[float] = None
    phMax:                  Optional[float] = None
    ecMin:                  Optional[float] = None
    ecMax:                  Optional[float] = None
    temperaturaAguaMax:     Optional[float] = None
    temperaturaAmbienteMax: Optional[float] = None
    umidadeRelativaMin:     Optional[float] = None
    nivelAguaMin:           Optional[float] = None
