print("🔥🔥🔥 CARGUE EL ADMIN.PY CORRECTO 🔥🔥🔥")

from sqlite3 import IntegrityError

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from database import SesionLocal
from models import RolEnum, Turno, Horario, Servicio
from auth.deps import admin_required, barbero_required
from routers.calendario import ZONA, RegistroManualRequest
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
        .options(
            joinedload(Turno.servicio),
            joinedload(Turno.barbero)
        )
        .order_by(Turno.fecha.desc(), Turno.hora.desc())
        .all()
    )

    return [
        {
            "id": t.id,
            "nombre": t.nombre,
            "telefono": t.telefono,
            "fecha": t.fecha.isoformat() if t.fecha else None,
            "hora": t.hora.strftime("%H:%M") if t.hora else None,
            "servicio": t.servicio.nombre,
            "precio": t.precio,
            "barbero": t.barbero.nombre if t.barbero else None,
            "barbero_id": t.barbero_id,
            "es_manual": t.es_manual,
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

    # 🔥 Horario puede ser NULL (turnos manuales)
    horario = None
    if turno.horario_id:
        horario = db.query(Horario).filter_by(id=turno.horario_id).first()

    # Guardamos datos antes de borrar
    servicio = turno.servicio
    nombre = turno.nombre

    # 🔓 Liberar horario solo si existe
    if horario:
        horario.disponible = True

    # 📧 EMAIL DE CANCELACIÓN
    try:
        if turno.usuario and turno.usuario.email:
            enviar_email_cancelacion(
                destino=turno.usuario.email,
                nombre=nombre,
                fecha=horario.fecha if horario else turno.fecha,
                hora=horario.hora if horario else turno.hora,
                servicio=servicio
            )
            print("📧 Email de cancelación enviado")
        else:
            print("⚠️ Turno sin email asociado")
    except Exception as e:
        print("❌ Error enviando email:", e)

    # 🗑️ Eliminar turno
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

@router.get("/calendario-admin/{barbero_id}")
def calendario_admin(
    barbero_id: int,
    db: Session = Depends(get_db),
    user=Depends(admin_required),
):
    horarios = (
        db.query(Horario)
        .filter(Horario.barbero_id == barbero_id)
        .order_by(Horario.fecha, Horario.hora)
        .all()
    )

    return [
        {
            "id": h.id,
            "fecha": h.fecha.isoformat(),
            "hora": h.hora.strftime("%H:%M"),
            "disponible": h.disponible,
            "barbero_id": h.barbero_id,
        }
        for h in horarios
    ]

@router.post("/registros-manuales")
def crear_registro_manual(
    data: RegistroManualRequest,
    db: Session = Depends(get_db),
    user=Depends(barbero_required)
):
    

    try:

        servicio = (
            db.query(Servicio)
            .filter(
                Servicio.id == data.servicio_id,
                Servicio.activo == True
            )
            .first()
        )

        if not servicio:
            raise HTTPException(
                status_code=400,
                detail="Servicio inválido"
            )

        turno = Turno(
            nombre=data.nombre,
            telefono="",
            servicio_id=data.servicio_id,
            precio=servicio.precio,
            horario_id=None,
            fecha=data.fecha,
            hora=data.hora,
            barbero_id=user.id,
            usuario_id=None,
            es_manual=True
        )

        db.add(turno)
        db.commit()
        db.refresh(turno)

        return {
            "ok": True,
            "turno_id": turno.id
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error interno"
        )

    
@router.get("/ganancias")
def ver_ganancias(
    tipo: str,
    fecha: str | None = None,
    mes: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(admin_required),
):
    query = db.query(Turno)

    if tipo == "dia":
        dia = date.fromisoformat(fecha)

        query = query.filter(Turno.fecha == dia)

    elif tipo == "mes":
        y, m = map(int, mes.split("-"))

        query = query.filter(
            func.extract("year", Turno.fecha) == y,
            func.extract("month", Turno.fecha) == m,
        )

    turnos = query.all()

    facturacion_total = 0
    ganancia_admin_propia = 0
    ganancia_admin_alquiler = 0
    ganancia_barberos = 0

    for t in turnos:

        facturacion_total += t.precio

        if t.barbero and t.barbero.rol == RolEnum.admin:
            ganancia_admin_propia += t.precio
        else:
            ganancia_admin_alquiler += t.precio * 0.40
            ganancia_barberos += t.precio * 0.60

    return {
        "facturacion_total": round(facturacion_total, 2),
        "ganancia_admin_propia": round(ganancia_admin_propia, 2),
        "ganancia_admin_alquiler": round(ganancia_admin_alquiler, 2),
        "ganancia_barberos": round(ganancia_barberos, 2),
    }

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
            .filter(Turno.fecha == dia)
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
            .filter(
                func.extract("year", Turno.fecha) == y,
                func.extract("month", Turno.fecha) == m,
            )
            .group_by(Servicio.nombre)
            .all()
        )

    else:
        return []

    return [
        {"servicio": r.servicio, "total": float(r.total)}
        for r in resultados
    ]

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
        db.query(Turno)
        .join(Turno.servicio)
        .filter(
            Turno.fecha >= inicio,
            Turno.fecha < fin
        )
    )

    if servicio:
        query = query.filter(Servicio.nombre == servicio)

    resultados = query.all()

    detalle = []

    for t in resultados:

        if t.barbero and t.barbero.rol == RolEnum.admin:
            admin_propia = t.precio
            admin_alquiler = 0
            barbero = 0
        else:
            admin_propia = 0
            admin_alquiler = t.precio * 0.40
            barbero = t.precio * 0.60

        detalle.append(
            {
                "nombre": t.nombre,
                "servicio": t.servicio.nombre,
                "precio": t.precio,
                "admin_propia": round(admin_propia, 2),
                "admin_alquiler": round(admin_alquiler, 2),
                "barbero": round(barbero, 2),
            }
        )

    return detalle
@router.get("/estadisticas/dia")
def clientes_por_dia(
    fecha: str,
    db: Session = Depends(get_db),
    user=Depends(admin_required),
):
    fecha_date = date.fromisoformat(fecha)

    total = (
        db.query(func.count(Turno.id))
        .filter(Turno.fecha == fecha_date)
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
            Turno.fecha.label("fecha"),
            func.count(Turno.id).label("clientes"),
            func.coalesce(func.sum(Turno.precio), 0).label("total")
        )
        .filter(
            func.extract("year", Turno.fecha) == anio,
            func.extract("month", Turno.fecha) == mes,
        )
        .group_by(Turno.fecha)
        .order_by(Turno.fecha)
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

