from dataclasses import dataclass
from typing import Optional


@dataclass
class Usuario:
    # Para contas Google, o `sub` do token: nunca muda, mesmo se a pessoa
    # trocar de e-mail. Por isso o e-mail nao e chave de nada.
    id: str
    email: Optional[str] = None
    nome: Optional[str] = None
