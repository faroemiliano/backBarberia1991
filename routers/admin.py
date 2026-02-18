from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import SesionLocal
from models import Turno, Horario, Servicio
from auth.deps import admin_required
from utils.email import enviar_email_cancelacion
from utils.email import enviar_email_edicion
from datetime import date, timedelta, datetime
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
    tipo: str,
    fecha: str | None = None,
    mes: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(admin_required),
):
    if tipo == "dia":
        dia = date.fromisoformat(fecha)

        print("---- TURNOS EN DB ----")
        turnos = db.query(Turno).limit(20).all()
        for t in turnos:
            print("turno:", t.id, "horario_id:", t.horario_id, "precio:", t.precio)

        print("---- HORARIOS ----")
        horarios = db.query(Horario).limit(20).all()
        for h in horarios:
            print("horario:", h.id, "fecha:", h.fecha)
        total = (
            db.query(func.coalesce(func.sum(Turno.precio), 0))
            .join(Turno.horario)
            .filter(Horario.fecha == dia)
            .scalar()
        )

    elif tipo == "mes":
        y, m = map(int, mes.split("-"))

        total = (
            db.query(func.coalesce(func.sum(Turno.precio), 0))
            .join(Turno.horario)
            .filter(
                func.extract("year", Horario.fecha) == y,
                func.extract("month", Horario.fecha) == m,
            )
            .scalar()
        )

    else:
        total = 0

    return {"total": float(total)}

@router.get("/ganancias/grafico")
def ganancias_grafico(
    tipo: str,
    fecha: str | None = None,
    mes: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(admin_required),
):
    if tipo == "dia":
        dia = date.fromisoformat(fecha)

        resultados = (
            db.query(
                Servicio.nombre.label("servicio"),
                func.sum(Turno.precio).label("total")
            )
            .join(Turno.servicio)
            .join(Turno.horario)
            .filter(Horario.fecha == dia)
            .group_by(Servicio.nombre)
            .all()
        )

    elif tipo == "mes":
        y, m = map(int, mes.split("-"))

        resultados = (
            db.query(
                Servicio.nombre.label("servicio"),
                func.sum(Turno.precio).label("total")
            )
            .join(Turno.servicio)
            .join(Turno.horario)
            .filter(
                func.extract("year", Horario.fecha) == y,
                func.extract("month", Horario.fecha) == m,
            )
            .group_by(Servicio.nombre)
            .all()
        )
    else:
        return []

    return [{"servicio": r.servicio, "total": float(r.total)} for r in resultados]

@router.get("/ganancias/detalle")
def detalle_ganancias(
    fecha: str,
    servicio: str = None,
    db: Session = Depends(get_db),
    user=Depends(admin_required),
):
    base = date.fromisoformat(fecha)
    inicio = base
    fin = base + timedelta(days=1)

    query = (
        db.query(
            Turno.nombre,
            Servicio.nombre.label("servicio"),
            Turno.precio
        )
        .join(Turno.servicio)
        .join(Turno.horario)
        .filter(Horario.fecha >= inicio, Horario.fecha < fin)
    )

    if servicio:
        query = query.filter(Servicio.nombre == servicio)

    resultados = query.all()

    return [
        {"nombre": r.nombre, "servicio": r.servicio, "precio": r.precio}
        for r in resultados
    ]
@router.get("/estadisticas/dia")
def clientes_por_dia(
    fecha: str,
    db: Session = Depends(get_db),
    user=Depends(admin_required),
):
    fecha_date = date.fromisoformat(fecha)

    total = (
        db.query(func.count(Turno.id))
        .join(Turno.horario)
        .filter(Horario.fecha == fecha_date)
        .scalar()
    )

    return {
        "fecha": fecha,
        "total_clientes": total
    }

# =========================
# RESUMEN MENSUAL (CALENDARIO)
# =========================
@router.get("/estadisticas/mes")
def resumen_mes(
    anio: int,
    mes: int,
    db: Session = Depends(get_db),
    user=Depends(admin_required),
):
    resultados = (
        db.query(
            Horario.fecha.label("fecha"),
            func.count(Turno.id).label("clientes"),
            func.coalesce(func.sum(Turno.precio), 0).label("total")
        )
        .outerjoin(Turno, Turno.horario_id == Horario.id)
        .filter(
            func.extract("year", Horario.fecha) == anio,
            func.extract("month", Horario.fecha) == mes,
        )
        .group_by(Horario.fecha)
        .order_by(Horario.fecha)
        .all()
    )

    dias = [
        {
            "fecha": r.fecha.isoformat(),
            "clientes": r.clientes,
            "ganancia": float(r.total),
        }
        for r in resultados
    ]

    total_mes = sum(d["ganancia"] for d in dias)
    clientes_mes = sum(d["clientes"] for d in dias)

    return {
        "anio": anio,
        "mes": mes,
        "clientes_mes": clientes_mes,
        "ganancia_mes": total_mes,
        "dias": dias
    }
