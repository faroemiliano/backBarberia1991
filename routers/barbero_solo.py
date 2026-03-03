
# =========================
# PANEL DE BARBERO (SU TURNOS Y GANANCIAS)
# =========================
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.deps import barbero_required
from auth.security import decode_token
from database import get_db
from models import Turno, Usuario, Horario, Servicio
from pydantic import BaseModel

from schemas import HorarioOut

router = APIRouter()

class EditarTurnoRequest(BaseModel):
    fecha: Optional[date] = None
    hora: Optional[str] = None
    servicio_id: Optional[int] = None
    

@router.get("/panel-barbero")
def panel_barbero(
    db: Session = Depends(get_db),
    user=Depends(barbero_required),  # 🔥 mejor usar dependencia
):
    # turnos solo del barbero logueado
    turnos = db.query(Turno).filter(
        Turno.barbero_id == user.id
    ).all()

    hoy = date.today()

    dinero_diario = sum(
        t.precio for t in turnos
        if t.horario.fecha == hoy
    )

    dinero_mensual = sum(
        t.precio for t in turnos
        if t.horario.fecha.month == hoy.month
        and t.horario.fecha.year == hoy.year
    )

    return {
        "turnos": [
            {
                "id": t.id,
                "cliente": t.nombre,
                "telefono": t.telefono,
                "fecha": t.horario.fecha.isoformat(),
                "hora": t.horario.hora.strftime("%H:%M"),
                "horario_id": t.horario.id,
                "servicio": t.servicio.nombre,
                "precio": t.precio,
            }
            for t in turnos
        ],
        "dinero_diario": dinero_diario,
        "dinero_mensual": dinero_mensual,
    }

@router.put("/barbero/turnos/{turno_id}")
def editar_turno(
    turno_id: int,
    data: EditarTurnoRequest,
    db: Session = Depends(get_db),
    user=Depends(barbero_required),
):
    turno = db.query(Turno).filter(
        Turno.id == turno_id,
        Turno.barbero_id == user.id
    ).first()

    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    # =========================
    # CAMBIO DE HORARIO (OPCIONAL)
    # =========================
    if data.fecha and data.hora:

        nueva_hora = datetime.strptime(data.hora, "%H:%M").time()

        horario_actual = turno.horario

        # 🔥 Si es el mismo horario, no hacer nada
        if not (
            horario_actual.fecha == data.fecha
            and horario_actual.hora == nueva_hora
        ):

            nuevo_horario = db.query(Horario).filter(
                Horario.fecha == data.fecha,
                Horario.hora == nueva_hora,
                Horario.barbero_id == user.id,
                Horario.disponible == True
            ).first()

            if not nuevo_horario:
                raise HTTPException(
                    status_code=400,
                    detail="Horario no disponible"
                )

            # Liberar anterior
            horario_actual.disponible = True

            # Asignar nuevo
            nuevo_horario.disponible = False
            turno.horario = nuevo_horario

    # =========================
    # CAMBIO DE SERVICIO (OPCIONAL)
    # =========================
    if data.servicio_id:

        servicio = db.query(Servicio).filter(
            Servicio.id == data.servicio_id
        ).first()

        if not servicio:
            raise HTTPException(
                status_code=404,
                detail="Servicio no encontrado"
            )

        turno.servicio = servicio
        turno.precio = servicio.precio

    db.commit()
    db.refresh(turno)

    return {
        "ok": True,
        "mensaje": "Turno actualizado correctamente"
    }

@router.get("/barbero/horarios")
def get_horarios_barbero(
    db: Session = Depends(get_db),
    user=Depends(barbero_required)
):
    """
    Devuelve solo los horarios del barbero logueado
    Ordenados por fecha y hora
    """

    horarios = (
        db.query(Horario)
        .filter(Horario.barbero_id == user.id)
        .order_by(Horario.fecha.asc(), Horario.hora.asc())
        .all()
    )

    return [
        {
            "id": h.id,
            "fecha": h.fecha.isoformat(),
            "hora": h.hora.strftime("%H:%M"),
            "disponible": h.disponible
        }
        for h in horarios
    ]

@router.patch("/barbero/horarios/{horario_id}/toggle")
def toggle_horario_barbero(
    horario_id: int,
    db: Session = Depends(get_db),
    user=Depends(barbero_required)
):
    horario = db.query(Horario).filter(
        Horario.id == horario_id,
        Horario.barbero_id == user.id
    ).first()

    if not horario:
        raise HTTPException(status_code=404, detail="Horario no encontrado")

    # Cambiar disponible a True/False
    horario.disponible = not horario.disponible
    db.commit()
    db.refresh(horario)

    return {"ok": True, "disponible": horario.disponible}