from sqlalchemy import Column, DateTime, Integer, String

from app.infrastructure.persistence.database import Base


class PlantaModel(Base):
    __tablename__ = "plantas"

    id           = Column(Integer, primary_key=True, index=True)
    nome         = Column(String, nullable=False)
    tipo         = Column(String, nullable=False)
    data_plantio = Column(String, nullable=False)
    foto_url     = Column(String, nullable=True)


class EventoModel(Base):
    __tablename__ = "eventos"

    id        = Column(Integer, primary_key=True, index=True)
    nome      = Column(String, nullable=False, index=True)
    pagina    = Column(String, nullable=False)
    sessao    = Column(String, nullable=False, index=True)
    criado_em = Column(DateTime, nullable=False)


class InteresseModel(Base):
    __tablename__ = "interesses"

    id        = Column(Integer, primary_key=True, index=True)
    email     = Column(String, nullable=False, index=True)
    produto   = Column(String, nullable=False)
    sessao    = Column(String, nullable=False)
    criado_em = Column(DateTime, nullable=False)



class TorreModel(Base):
    """Copia local das torres, alimentada pelos eventos do servico de auth."""
    __tablename__ = "torres"

    id         = Column(String, primary_key=True)        # AT-<MAC>
    kit        = Column(String, nullable=False)          # basico | completo | pro
    dono_id    = Column(String, nullable=True, index=True)  # sub da conta Google
    apelido    = Column(String, nullable=True)
    versao     = Column(Integer, nullable=False, default=0)
    criada_em  = Column(DateTime, nullable=False)
    ativada_em = Column(DateTime, nullable=True)
