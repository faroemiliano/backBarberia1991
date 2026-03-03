from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract
from database import get_db
from models import RolEnum, Usuario, Turno
from auth.security import decode_token
from datetime import date
from passlib.context import CryptContext

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =========================
# HELPER VALIDAR ADMIN
# =========================
def get_admin_from_token(authorization: str, db: Session):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token inválido")

    token = authorization.replace("Bearer ", "").strip()
    payload = decode_token(token)

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    admin = db.query(Usuario).filter_by(
        id=user_id,
        rol=RolEnum.admin
    ).first()

    if not admin:
        raise HTTPException(status_code=403, detail="No autorizado")

    return admin


# =========================
# AUTORIZAR BARBERO (ADMIN)
# =========================
class AutorizarBarberoRequest(BaseModel):
    email: str


@router.post("/autorizar-barbero")
def autorizar_barbero(
    data: AutorizarBarberoRequest,
    db: Session = Depends(get_db),
    authorization: str = Header(...)
):
    get_admin_from_token(authorization, db)

    usuario = db.query(Usuario).filter_by(email=data.email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.rol = RolEnum.barbero
    db.commit()

    return {"ok": True, "mensaje": f"{data.email} ahora es barbero"}


# =========================
# VER TODOS LOS BARBEROS (ADMIN)
# =========================
@router.get("/barberos")
def ver_barberos(
    db: Session = Depends(get_db),
    authorization: str = Header(...)
):
    get_admin_from_token(authorization, db)

    barberos = db.query(Usuario).filter_by(
        rol=RolEnum.barbero
    ).all()

    return [
        {"id": b.id, "nombre": b.nombre, "email": b.email}
        for b in barberos
    ]


# =========================
# PANEL DE CUALQUIER BARBERO (ADMIN)
# =========================
@router.get("/panel-barbero/{barbero_id}")
def panel_barbero_admin(
    barbero_id: int,
    db: Session = Depends(get_db),
    authorization: str = Header(...)
):
    get_admin_from_token(authorization, db)

    barbero = db.query(Usuario).filter_by(
        id=barbero_id,
        rol=RolEnum.barbero
    ).first()

    if not barbero:
        raise HTTPException(status_code=404, detail="Barbero no encontrado")

    hoy = date.today()

    # 🔹 Turnos con joins optimizados
    turnos = (
        db.query(Turno)
        .options(joinedload(Turno.horario), joinedload(Turno.servicio))
        .filter(Turno.barbero_id == barbero.id)
        .all()
    )

    # 🔹 Dinero diario desde DB
    dinero_diario = (
        db.query(func.coalesce(func.sum(Turno.precio), 0))
        .join(Turno.horario)
        .filter(
            Turno.barbero_id == barbero.id,
            Turno.horario.has(fecha=hoy)
        )
        .scalar()
    )

    # 🔹 Turnos del mes
    turnos_mes = (
        db.query(Turno)
        .join(Turno.horario)
        .filter(
            Turno.barbero_id == barbero.id,
            extract("month", Turno.horario.property.mapper.class_.fecha) == hoy.month,
            extract("year", Turno.horario.property.mapper.class_.fecha) == hoy.year
        )
        .all()
    )

    dinero_mensual = sum(t.precio for t in turnos_mes)

    return {
        "barbero": {
            "id": barbero.id,
            "nombre": barbero.nombre,
            "email": barbero.email
        },
        "turnos": [
            {
                "id": t.id,
                "cliente": t.nombre,
                "telefono": t.telefono,
                "fecha": t.horario.fecha,
                "hora": t.horario.hora.strftime("%H:%M"),
                "servicio": t.servicio.nombre,
                "precio": t.precio,
            }
            for t in turnos
        ],
        "dinero_diario": dinero_diario,
        "dinero_mensual": dinero_mensual
    }