import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from app.domain.entities.kit import Kit, capacidades_do_kit

# "AT-" + MAC do ESP32 em hexadecimal (ex.: AT-24DCC3A1B2C4). Aceita de 4 a
# 16 caracteres para caber tambem ids de simulador e da torre legada. O
# formato fechado impede que um tópico qualquer vire uma "torre".
_PADRAO_ID = re.compile(r"^AT-[0-9A-Z]{4,16}$")


def id_de_torre_valido(torre_id: str) -> bool:
    return bool(_PADRAO_ID.match(torre_id or ""))


@dataclass
class Torre:
    id: str
    kit: Kit
    dono_id: Optional[str] = None
    apelido: Optional[str] = None
    criada_em: Optional[datetime] = None
    ativada_em: Optional[datetime] = None

    @property
    def capacidades(self) -> List[str]:
        return capacidades_do_kit(self.kit)

    @property
    def ativada(self) -> bool:
        return self.dono_id is not None

    def pertence_a(self, usuario_id: str) -> bool:
        return self.dono_id is not None and self.dono_id == usuario_id
