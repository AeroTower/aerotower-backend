"""Codigo de ativacao impresso no adesivo da torre.

Regras:
* aleatorio (modulo `secrets`), nunca derivado do MAC — quem ve a torre nao
  pode adivinhar o codigo;
* alfabeto sem caracteres ambiguos (0/O, 1/I/L), porque a pessoa digita;
* 8 caracteres de 32 simbolos = 40 bits, mostrado como XXXX-XXXX;
* o banco guarda so o hash: um vazamento da tabela nao entrega codigos
  ainda nao usados.
"""
import hashlib
import secrets

ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
TAMANHO = 8


def gerar_codigo() -> str:
    bruto = "".join(secrets.choice(ALFABETO) for _ in range(TAMANHO))
    return f"{bruto[:4]}-{bruto[4:]}"


def normalizar_codigo(codigo: str) -> str:
    """Aceita o que a pessoa digitar: minusculas, espacos, com ou sem hifen."""
    return "".join(c for c in (codigo or "").upper() if c.isalnum())


def hash_codigo(codigo: str) -> str:
    return hashlib.sha256(normalizar_codigo(codigo).encode("utf-8")).hexdigest()


def formato_valido(codigo: str) -> bool:
    limpo = normalizar_codigo(codigo)
    return len(limpo) == TAMANHO and all(c in ALFABETO for c in limpo)
