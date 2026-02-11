from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import SesionLocal
from models import Turno, Horario, Servicio
from auth.deps import admin_required
from utils.email import enviar_email_cancelacion
from utils.email import enviar_email_edicion
from datetime import date, timedelta
from sqlalchemy import func
from schemas import EditarTurno
from database import get_db

router = APIRouter()





# =========================
# VER TODOS LOS TURNOS
# =========================
@router.get("/turnos")
def ver_turnos(
    db: Session = Depends(get_db),
    user=Depends(admin_required)
):
    turnos = (
        db.query(Turno)
        .join(Horario)
        .order_by(Horario.fecha, Horario.hora)
        .all()
    )

    return [
        {
            "id": t.id,
            "nombre": t.nombre,
            "telefono": t.telefono,
            "fecha": t.horario.fecha.isoformat(),
            "hora": t.horario.hora.strftime("%H:%M"),
            "servicio": t.servicio.nombre,
            "precio": t.precio,  # ✅ AGREGADO
        }
        for t in turnos
    ]


# =========================
# CANCELAR TURNO (ADMIN)
# =========================
@router.delete("/cancelar/{turno_id}")
def cancelar_turno(
    turno_id: int,
    db: Session = Depends(get_db),
    user=Depends(admin_required)
):
    turno = db.query(Turno).filter_by(id=turno_id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    horario = db.query(Horario).filter_by(id=turno.horario_id).first()
    if not horario:
        raise HTTPException(status_code=404, detail="Horario no encontrado")

    # Guardamos datos ANTES de borrar
    servicio = turno.servicio
    nombre = turno.nombre

    # Liberar horario
    horario.disponible = True

    # 📧 EMAIL DE CANCELACIÓN
    try:
        if turno.usuario and turno.usuario.email:
            enviar_email_cancelacion(
                destino=turno.usuario.email,
                nombre=nombre,
                fecha=horario.fecha,
                hora=horario.hora,
                servicio=servicio  
            )
            print("📧 Email de cancelación enviado")
        else:
            print("⚠️ Turno sin email asociado")
    except Exception as e:
        print("❌ Error enviando email:", e)

    # Eliminar turno
    db.delete(turno)
    db.commit()

    return {
        "ok": True,
        "mensaje": "Turno cancelado correctamente"
    }

# =========================
# EDITAR TURNO (ADMIN)
# =========================
@router.patch("/turnos/{turno_id}")
def editar_turno(
    turno_id: int,
    data: EditarTurno,
    db: Session = Depends(get_db),
    user=Depends(admin_required)
):
    turno = db.query(Turno).filter_by(id=turno_id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    servicio_anterior = turno.servicio.nombre
    horario_actual = turno.horario
    fecha_anterior = horario_actual.fecha
    hora_anterior = horario_actual.hora

    # ======================
    # CAMBIAR HORARIO
    # ======================
    if data.horario_id is not None:
        nuevo_horario = db.query(Horario).filter_by(id=data.horario_id).first()
        if not nuevo_horario or not nuevo_horario.disponible:
            raise HTTPException(status_code=400, detail="Horario no disponible")

        horario_actual.disponible = True
        nuevo_horario.disponible = False
        turno.horario_id = nuevo_horario.id
    else:
        nuevo_horario = horario_actual

    # ======================
    # CAMBIAR SERVICIO
    # ======================
    if data.servicio_id is not None:
        servicio = db.query(Servicio).filter(
            Servicio.id == data.servicio_id,
            Servicio.activo.is_(True)
        ).first()

        if not servicio:
            raise HTTPException(status_code=400, detail="Servicio inválido")

        turno.servicio_id = servicio.id
        turno.precio = servicio.precio
        servicio_nuevo = servicio.nombre
    else:
        servicio_nuevo = servicio_anterior

    # ======================
    # TELEFONO
    # ======================
    if data.telefono is not None:
        turno.telefono = data.telefono

    # ======================
    # PRECIO MANUAL
    # ======================
    if data.precio is not None:
        turno.precio = data.precio

    db.commit()

    # ======================
    # EMAIL
    # ======================
    try:
        if turno.usuario and turno.usuario.email:
            enviar_email_edicion(
                destino=turno.usuario.email,
                nombre=turno.nombre,
                fecha_anterior=fecha_anterior,
                hora_anterior=hora_anterior,
                fecha_nueva=nuevo_horario.fecha,
                hora_nueva=nuevo_horario.hora,
                servicio_anterior=servicio_anterior,
                servicio_nuevo=servicio_nuevo,
            )
    except Exception as e:
        print("Email edición error:", e)

    return {
        "ok": True,
        "mensaje": "Turno actualizado correctamente"
    }


@router.patch("/horarios/{horario_id}/toggle")
def toggle_horario(
    horario_id: int,
    db: Session = Depends(get_db),
    user=Depends(admin_required),
):
    horario = db.query(Horario).filter_by(id=horario_id).first()
    if not horario:
        raise HTTPException(status_code=404, detail="Horario no encontrado")

    # ❌ No permitir bloquear si ya hay turno
    turno_existente = db.query(Turno).filter_by(horario_id=horario.id).first()
    if turno_existente:
        raise HTTPException(
            status_code=400,
            detail="No se puede bloquear un horario con turno asignado"
        )

    horario.disponible = not horario.disponible
    db.commit()

    return {
        "id": horario.id,
        "fecha": horario.fecha.isoformat(),
        "hora": horario.hora.strftime("%H:%M"),
        "disponible": horario.disponible,
    }

@router.get("/calendario")
def calendario_admin(
    db: Session = Depends(get_db),
    user=Depends(admin_required),
):
    horarios = (
        db.query(Horario)
        .order_by(Horario.fecha, Horario.hora)
        .all()
    )

    return [
        {
            "id": h.id,
            "fecha": h.fecha.isoformat(),
            "hora": h.hora.strftime("%H:%M"),
            "disponible": h.disponible,
        }
        for h in horarios
    ]

@router.get("/ganancias")
def ver_ganancias(
    tipo: str = Query(..., regex="^(dia|semana|mes)$"),
    db: Session = Depends(get_db),
    user=Depends(admin_required),
):
    hoy = date.today()

    if tipo == "dia":
        inicio = hoy
        fin = hoy

    elif tipo == "semana":
        inicio = hoy - timedelta(days=hoy.weekday())
        fin = inicio + timedelta(days=6)

    else:  # mes
        inicio = hoy.replace(day=1)
        if inicio.month == 12:
            fin = inicio.replace(year=inicio.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fin = inicio.replace(month=inicio.month + 1, day=1) - timedelta(days=1)

    total = (
        db.query(func.coalesce(func.sum(Turno.precio), 0))
        .join(Horario)
        .filter(Horario.fecha.between(inicio, fin))
        .scalar()
    )

    return {
        "tipo": tipo,
        "desde": inicio.isoformat(),
        "hasta": fin.isoformat(),
        "total": total,
    }



@router.get("/ganancias/grafico")
def ganancias_grafico(
    tipo: str = "dia",
    fecha: str = None,  # <-- nuevo parámetro para tipo "dia"
    mes: str = None,
    db: Session = Depends(get_db)
):
    """
    Devuelve ganancias para gráfico de torta agrupadas por servicio.
    tipo: "dia", "semana", "mes"
    fecha: "YYYY-MM-DD" para tipo=dia
    mes: "YYYY-MM" para tipo=mes
    """
    hoy = date.today()

    if tipo == "dia":
        if fecha:
            start = end = date.fromisoformat(fecha)
        else:
            start = end = hoy
    elif tipo == "semana":
        if fecha:
            d = date.fromisoformat(fecha)
        else:
            d = hoy
        start = d - timedelta(days=d.weekday())
        end = start + timedelta(days=6)
    elif tipo == "mes":
        if mes:  # ej: "2026-02"
            y, m = map(int, mes.split("-"))
            start = date(y, m, 1)
        else:
            start = date(hoy.year, hoy.month, 1)
        # último día del mes
        if start.month == 12:
            end = date(start.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(start.year, start.month + 1, 1) - timedelta(days=1)
    else:
        return {"error": "tipo inválido"}

    resultados = (
        db.query(
            Servicio.nombre.label("servicio"),
            func.sum(Turno.precio).label("total")
        )
        .join(Turno.servicio)
        .join(Turno.horario)
        .filter(Turno.horario.has(Horario.fecha.between(start, end)))
        .group_by(Servicio.nombre)
        .all()
    )

    return [{"servicio": r.servicio, "total": r.total} for r in resultados]

@router.get("/ganancias/detalle")
def detalle_ganancias(
    fecha: str,
    servicio: str = None,  # opcional
    db: Session = Depends(get_db),
    user=Depends(admin_required),
):
    query = (
        db.query(
            Turno.nombre,
            Servicio.nombre.label("servicio"),
            Turno.precio
        )
        .join(Turno.servicio)
        .join(Turno.horario)
        .filter(Horario.fecha == date.fromisoformat(fecha))
    )

    # solo filtrar si se pasó un servicio
    if servicio:
        query = query.filter(Servicio.nombre == servicio)

    resultados = query.all()

    return [
        {
            "nombre": r.nombre,
            "servicio": r.servicio,
            "precio": r.precio,
        }
        for r in resultados
    ]