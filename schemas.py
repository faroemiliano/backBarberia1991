from pydantic import BaseModel
from typing import Optional

class EditarTurno(BaseModel):
    horario_id: Optional[int] = None
    servicio_id: Optional[int] = None
    telefono: Optional[str] = None
    precio: Optional[float] = None