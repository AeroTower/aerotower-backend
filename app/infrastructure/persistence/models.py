from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

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


class UsuarioModel(Base):
    __tablename__ = "usuarios"

    # `sub` do Google (ou "dev:..." no modo de desenvolvimento)
    id        = Column(String, primary_key=True)
    email     = Column(String, nullable=True, index=True)
    nome      = Column(String, nullable=True)
    criado_em = Column(DateTime, nullable=False)


class TorreModel(Base):
    __tablename__ = "torres"

    id          = Column(String, primary_key=True)             # AT-<MAC>
    kit         = Column(String, nullable=False)               # basico | completo | pro
    # Hash do codigo do adesivo. Vira NULL quando a torre e ativada: o
    # codigo vale uma vez so.
    codigo_hash = Column(String, nullable=True, unique=True, index=True)
    dono_id     = Column(String, ForeignKey("usuarios.id"), nullable=True, index=True)
    apelido     = Column(String, nullable=True)
    criada_em   = Column(DateTime, nullable=False)
    ativada_em  = Column(DateTime, nullable=True)
