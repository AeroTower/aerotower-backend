from sqlalchemy.orm import Session


class RepositorioSqlAlchemy:
    """Base dos repositorios SQL: guarda a sessao e o jeito de gravar.

    Antes, cada repositorio repetia add -> commit -> refresh em todo metodo
    de criacao. Ficando num lugar so, uma mudanca (ex.: rollback em caso de
    erro) vale para todos.
    """

    def __init__(self, session: Session):
        self._session = session

    def _salvar(self, modelo):
        """Grava o modelo e devolve ele recarregado do banco (com id)."""
        self._session.add(modelo)
        self._commit()
        self._session.refresh(modelo)
        return modelo

    def _commit(self) -> None:
        # Se o commit falhar (ex.: campo obrigatorio vazio), a sessao fica
        # num estado invalido e QUALQUER consulta seguinte falha tambem.
        # O rollback deixa a sessao utilizavel de novo; o erro continua
        # subindo para quem chamou.
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
