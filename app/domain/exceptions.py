class ErroDeDominio(Exception):
    pass


class PlantaNaoEncontrada(ErroDeDominio):
    def __init__(self, planta_id: int):
        self.planta_id = planta_id
        super().__init__(f"Planta {planta_id} não encontrada.")


class FormatoDeFotoInvalido(ErroDeDominio):
    def __init__(self, extensoes_aceitas):
        self.extensoes_aceitas = extensoes_aceitas
        super().__init__("Formato inválido. Use jpg, jpeg, png ou webp.")


class NenhumDadoDisponivel(ErroDeDominio):
    def __init__(self, mensagem: str):
        super().__init__(mensagem)


class FalhaNaPublicacao(ErroDeDominio):
    def __init__(self, codigo: int):
        self.codigo = codigo
        super().__init__(f"Falha ao publicar no MQTT. Código: {codigo}")


class EmailInvalido(ErroDeDominio):
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"E-mail inválido: {email}")


class EventoInvalido(ErroDeDominio):
    def __init__(self, motivo: str):
        super().__init__(motivo)


# ── Torres, usuarios e acesso ──────────────

class NaoAutenticado(ErroDeDominio):
    def __init__(self, motivo: str = "Login necessário."):
        super().__init__(motivo)


class TorreNaoEncontrada(ErroDeDominio):
    # Usada tambem quando a torre existe mas e de outra pessoa: responder
    # 403 contaria a um curioso que aquele id existe.
    def __init__(self, torre_id: str):
        self.torre_id = torre_id
        super().__init__(f"Torre {torre_id} não encontrada.")


class CodigoDeAtivacaoInvalido(ErroDeDominio):
    def __init__(self):
        super().__init__("Código de ativação inválido ou já utilizado.")


class TorreJaCadastrada(ErroDeDominio):
    def __init__(self, torre_id: str):
        super().__init__(f"A torre {torre_id} já está cadastrada.")


class IdDeTorreInvalido(ErroDeDominio):
    def __init__(self, torre_id: str):
        super().__init__(
            f"Id de torre inválido: {torre_id!r}. Use o formato AT-<MAC>, ex.: AT-24DCC3A1B2C4."
        )


class AcessoNegado(ErroDeDominio):
    def __init__(self, motivo: str = "Acesso negado."):
        super().__init__(motivo)
