from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Date,
    Time,
    ForeignKey,
    UniqueConstraint,
    Index,
    Float,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# ======================
# USUARIOS
# ======================

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password = Column(String, nullable=True)
    is_admin = Column(Boolean, nullable=False, default=False)

    turnos = relationship(
        "Turno",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Usuario {self.id} {self.email}>"

# ======================
# HORARIOS BASE
# ======================

class HorarioBase(Base):
    __tablename__ = "horarios_base"

    id = Column(Integer, primary_key=True)
    dia_semana = Column(String(15), nullable=False)
    hora = Column(Time, nullable=False)

    __table_args__ = (
        UniqueConstraint("dia_semana", "hora", name="uq_dia_hora_base"),
    )

    def __repr__(self):
        return f"<HorarioBase {self.dia_semana} {self.hora}>"

# ======================
# HORARIOS (CALENDARIO)
# ======================

class Horario(Base):
    __tablename__ = "horarios"

    id = Column(Integer, primary_key=True)
    fecha = Column(Date, nullable=False, index=True)
    hora = Column(Time, nullable=False)
    disponible = Column(Boolean, nullable=False, default=True)

    turno = relationship(
        "Turno",
        back_populates="horario",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("fecha", "hora", name="uq_fecha_hora"),
        Index("ix_fecha_disponible", "fecha", "disponible"),
    )

    def __repr__(self):
        return f"<Horario {self.fecha} {self.hora} disp={self.disponible}>"

# ======================
# SERVICIOS
# ======================

class Servicio(Base):
    __tablename__ = "servicios"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    precio = Column(Float, nullable=False)
    activo = Column(Boolean, nullable=False, default=True)

    turnos = relationship(
        "Turno",
        back_populates="servicio",
    )

    def __repr__(self):
        return f"<Servicio {self.nombre} ${self.precio}>"

# ======================
# TURNOS
# ======================

class Turno(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True)

    nombre = Column(String(100), nullable=False)
    telefono = Column(String(30), nullable=False)

    horario_id = Column(
        Integer,
        ForeignKey("horarios.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    usuario_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )

    servicio_id = Column(
        Integer,
        ForeignKey("servicios.id"),
        nullable=False,
    )

    # snapshot del precio al momento del turno
    precio = Column(Float, nullable=False)

    horario = relationship("Horario", back_populates="turno")
    usuario = relationship("Usuario", back_populates="turnos")
    servicio = relationship("Servicio", back_populates="turnos")

    def __repr__(self):
        return f"<Turno {self.id} horario={self.horario_id}>"
