from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class Presenca:
    """O que a propria torre diz de si pelo MQTT.

    `online` vem do topico status (o broker publica "offline" sozinho via
    LWT quando a torre cai). `info` vem do topico info: firmware, kit
    compilado e sensores que o ESP32 encontrou no boot.
    """
    online: Optional[bool] = None
    info: Dict[str, Any] = field(default_factory=dict)
    atualizado_em: Optional[datetime] = None
