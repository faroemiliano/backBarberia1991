# routers/debug.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Usuario, Turno, Servicio
from datetime import datetime

router = APIRouter()

# 🔹 Todos los usuarios
@router.get("/debug/usuarios")
def debug_usuarios(db: Session = Depends(get_db)):
    return db.query(Usuario).all()

# 🔹 Todos los turnos
@router.get("/debug/turnos")
def debug_turnos(db: Session = Depends(get_db)):
    return db.query(Turno).all()

# 🔹 Todos los servicios
@router.get("/debug/servicios")
def debug_servicios(db: Session = Depends(get_db)):
    return db.query(Servicio).all()

# 🔹 Turnos por mes (para gráfico)
@router.get("/debug/grafico/mes")
def debug_grafico_mes(db: Session = Depends(get_db)):
    # Agrupa por mes y cuenta turnos
    resultados = (
        db.query(
            func.date_trunc("month", Turno.fecha).label("mes"),
            func.count(Turno.id).label("cantidad")
        )
        .group_by("mes")
        .order_by("mes")
        .all()
    )

    return [
        {"mes": r.mes.strftime("%Y-%m"), "cantidad": r.cantidad}
        for r in resultados
    ]
