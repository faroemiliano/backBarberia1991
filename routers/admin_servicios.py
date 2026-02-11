# routers/admin_servicios.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Servicio

router = APIRouter(
    prefix="/admin/servicios",
    tags=["Admin - Servicios"],
)

@router.get("")
def listar_servicios(db: Session = Depends(get_db)):
    return db.query(Servicio).order_by(Servicio.id).all()


@router.patch("/{servicio_id}")
def actualizar_servicio(
    servicio_id: int,
    payload: dict,
    db: Session = Depends(get_db),
):
    servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()

    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    if "precio" in payload:
        servicio.precio = payload["precio"]

    if "activo" in payload:
        servicio.activo = payload["activo"]

    db.commit()
    db.refresh(servicio)

    return servicio
