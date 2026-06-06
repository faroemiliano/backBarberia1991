from pydantic import BaseModel
from typing import Optional

class EditarTurno(BaseModel):
    horario_id: Optional[int] = None
    servicio_id: Optional[int] = None
    telefono: Optional[str] = None
    precio: Optional[float] = None

class HorarioOut(BaseModel):
    id: int
    fecha: str
    hora: str
    disponible: bool

    class Config:
        from_attributes = True  # 👈 agregar esto

class ProfesionalOut(BaseModel):
    id: int
    nombre: str
    foto_url: Optional[str] = None

    class Config:
        from_attributes = True

class RegistroManualCreate(BaseModel):
    nombre: str
    servicio_id: int
    precio: float
    observaciones: str | None = None        