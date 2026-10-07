# routers/admin_servicios.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth.deps import admin_required
from database import get_db
from models import AuditoriaServicio, Servicio, Usuario

router = APIRouter(prefix="/admin/servicios", tags=["Admin"])


class ServicioUpdate(BaseModel):
    precio: float | None = Field(default=None, gt=0, le=1_000_000)
    activo: bool | None = None


def registrar_auditoria(
    db: Session,
    servicio: Servicio,
    admin: Usuario,
    request: Request,
    accion: str,
    precio_anterior: float | None,
    activo_anterior: bool | None,
) -> None:
    db.add(
        AuditoriaServicio(
            servicio_id=servicio.id,
            admin_id=admin.id,
            accion=accion,
            precio_anterior=precio_anterior,
            precio_nuevo=servicio.precio,
            activo_anterior=activo_anterior,
            activo_nuevo=servicio.activo,
            ip=request.client.host if request.client else None,
        )
    )


@router.get("")
def listar_servicios(
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(admin_required),
):
    return db.query(Servicio).order_by(Servicio.id).all()


@router.get("/auditoria")
def listar_auditoria_servicios(
    limite: int = 100,
    db: Session = Depends(get_db),
    _admin: Usuario = Depends(admin_required),
):
    limite = max(1, min(limite, 500))
    return (
        db.query(AuditoriaServicio)
        .order_by(AuditoriaServicio.creado_en.desc(), AuditoriaServicio.id.desc())
        .limit(limite)
        .all()
    )


@router.patch("/{servicio_id}")
def actualizar_servicio(
    servicio_id: int,
    payload: ServicioUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(admin_required),
):
    servicio = db.query(Servicio).filter(Servicio.id == servicio_id).first()

    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    if payload.precio is None and payload.activo is None:
        raise HTTPException(status_code=422, detail="Indicá precio o estado para actualizar.")

    precio_anterior = servicio.precio
    activo_anterior = servicio.activo

    if payload.precio is not None:
        servicio.precio = payload.precio

    if payload.activo is not None:
        servicio.activo = payload.activo

    if servicio.precio != precio_anterior or servicio.activo != activo_anterior:
        registrar_auditoria(
            db,
            servicio,
            admin,
            request,
            "actualizacion_manual",
            precio_anterior,
            activo_anterior,
        )

    db.commit()
    db.refresh(servicio)

    return servicio
