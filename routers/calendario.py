from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import SesionLocal
from models import Horario, RolEnum, Turno, Usuario, Servicio
from auth.security import decode_token
from pydantic import BaseModel, Field
from datetime import date, timedelta, time
import calendar
from datetime import datetime
from database import get_db


from utils import horarios
from utils.email import enviar_email_confirmacion

router = APIRouter()



class SolicitudTurno(BaseModel):
    telefono: str = Field(..., min_length=8, max_length=20)
    servicio_id: int
    horario_id: int
    

# --------------------------------------------------
# OBTENER TODO EL CALENDARIO
# --------------------------------------------------
@router.get("/calendario/{barbero_id}")
def calendario(barbero_id: int, db: Session = Depends(get_db)):

    # 🔎 Validar que el profesional exista (admin o barbero)
    profesional = db.query(Usuario).filter(
        Usuario.id == barbero_id,
        Usuario.rol.in_([RolEnum.barbero, RolEnum.admin])
    ).first()

    if not profesional:
        raise HTTPException(
            status_code=404,
            detail="Profesional no encontrado"
        )

    hoy = date.today()

    horarios = (
        db.query(Horario)
        .filter(
            Horario.barbero_id == barbero_id,
            Horario.disponible == True,
            Horario.fecha >= hoy
        )
        .order_by(Horario.fecha, Horario.hora)
        .all()
    )

    # ⚠️ No devolver 404 si no hay horarios
    # Simplemente devolver lista vacía
    return [
        {
            "id": h.id,
            "fecha": h.fecha.isoformat(),
            "hora": h.hora.strftime("%H:%M"),
            "disponible": h.disponible,
        }
        for h in horarios
    ]
# --------------------------------------------------
# GENERAR TODO EL AÑO (UNA SOLA VEZ)
# --------------------------------------------------
@router.post("/preparar-calendario")
def preparar_calendario(db: Session = Depends(get_db)):

    from datetime import datetime, timedelta

    anio = date.today().year

    # 🔥 calcular próximo martes
    hoy = date.today()
    dias_hasta_martes = (1 - hoy.weekday()) % 7
    fecha_cambio = hoy + timedelta(days=dias_hasta_martes)

    inicio = fecha_cambio
    fin = date(anio, 12, 31)

    # 🔥 borrar SOLO horarios futuros disponibles (no rompe turnos)
    horarios = db.query(Horario).filter(
            Horario.hora == time(13, 40),
            Horario.disponible == True,
            Horario.fecha >= hoy
        ).all()

    for h in horarios:
        if h.fecha.weekday() in [4, 5]:
            db.delete(h)

    db.commit()

    barberos = db.query(Usuario).filter(
        Usuario.rol.in_([RolEnum.barbero, RolEnum.admin])
    ).all()

    if not barberos:
        raise HTTPException(status_code=400, detail="No hay barberos creados")

    creados = 0
    actual = inicio

    while actual <= fin:

        dia = actual.weekday()

        # 🎯 Martes a jueves
        if dia in [1, 2, 3]:
            franjas = [(11, 13, 40), (15, 20)]

        # 🎯 Viernes y sábado
        elif dia in [4, 5]:
            franjas = [(10, 13, 40), (15, 20)]

        else:
            actual += timedelta(days=1)
            continue

        for franja in franjas:
            if len(franja) == 2:
                inicio_h, fin_h = franja
                fin_m = 0
            else:
                inicio_h, fin_h, fin_m = franja

            inicio_dt = datetime.combine(actual, time(inicio_h, 0))
            fin_dt = datetime.combine(actual, time(fin_h, fin_m))

            horas_creadas = set()

            while inicio_dt <= fin_dt:

                hora_actual = inicio_dt.time()

                # 🚫 bloquear 13:40 SOLO viernes (4) y sábado (5)
                if dia in [4, 5] and hora_actual == time(13, 40):
                    inicio_dt += timedelta(minutes=40)
                    continue

           

                for barbero in barberos:

                    existe = db.query(Horario).filter(
                        Horario.fecha == actual,
                        Horario.hora == hora_actual,
                        Horario.barbero_id == barbero.id
                    ).first()

                    if not existe:
                        db.add(Horario(
                            fecha=actual,
                            hora=hora_actual,
                            disponible=True,
                            barbero_id=barbero.id
                        ))
                        creados += 1

                horas_creadas.add(hora_actual)

                # 🔥 salto de 40 minutos
                inicio_dt += timedelta(minutes=40)

            # 🔥 asegurar hora final (ej: 20:00)
            hora_final = time(fin_h, fin_m)

# 🚫 no agregar 13:40 en viernes y sábado
            if dia in [4, 5] and hora_final == time(13, 40):
                    pass
            elif hora_final not in horas_creadas:
                for barbero in barberos:
                    existe_final = db.query(Horario).filter(
                        Horario.fecha == actual,
                        Horario.hora == hora_final,
                        Horario.barbero_id == barbero.id
                    ).first()

                    if not existe_final:
                        db.add(Horario(
                            fecha=actual,
                            hora=hora_final,
                            disponible=True,
                            barbero_id=barbero.id
                        ))
                        creados += 1

        actual += timedelta(days=1)

    db.commit()

    return {
        "ok": True,
        "desde": str(fecha_cambio),
        "horarios_creados": creados
    }
# --------------------------------------------------
# GENERAR TODO EL AÑO (UNA SOLA VEZ)
# --------------------------------------------------

@router.post("/preparar-servicios")
def preparar_servicios(db: Session = Depends(get_db)):

    servicios_base = [
        {"nombre": "Corte", "precio": 15000},
        {"nombre": "Corte + Barba", "precio": 17000},
        {"nombre": "Barba", "precio": 13000},
        {"nombre": "Corte + Tintura", "precio": 800},
    ]

    creados = 0
    actualizados = 0
    reactivados = 0

    for s in servicios_base:
        servicio = db.query(Servicio).filter(Servicio.nombre == s["nombre"]).first()

        # NO EXISTE → CREAR
        if not servicio:
            db.add(Servicio(
                nombre=s["nombre"],
                precio=s["precio"],
                activo=True
            ))
            creados += 1
            continue

        # EXISTE PERO ESTABA DESACTIVADO → REACTIVAR
        if not servicio.activo:
            servicio.activo = True
            reactivados += 1

        # EXISTE PERO CAMBIÓ PRECIO → ACTUALIZAR
        if servicio.precio != s["precio"]:
            servicio.precio = s["precio"]
            actualizados += 1

    db.commit()

    return {
        "ok": True,
        "creados": creados,
        "actualizados": actualizados,
        "reactivados": reactivados
    }

# --------------------------------------------------
# RESERVAR TURNO
# --------------------------------------------------
ZONA = ZoneInfo("America/Argentina/Buenos_Aires")

@router.post("/reservar")
def reservar(
    data: SolicitudTurno,
    db: Session = Depends(get_db),
    authorization: str = Header(...)
):
    # 1️⃣ Validar Authorization
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token mal formado")

    token = authorization.replace("Bearer ", "").strip()
    payload = decode_token(token)

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    # 2️⃣ Buscar usuario
    usuario = db.query(Usuario).filter_by(id=user_id).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    if usuario.rol != RolEnum.cliente:
        raise HTTPException(
            status_code=403,
            detail="Solo los clientes pueden reservar turnos"
        )

    # 3️⃣ Buscar horario disponible
    horario = (
        db.query(Horario)
        .filter(
            Horario.id == data.horario_id,
            Horario.disponible == True
        )
        .first()
    )

    if not horario:
        raise HTTPException(status_code=400, detail="Horario no disponible")

    # 4️⃣ Validar que no sea fecha pasada (con timezone correcto)
    fecha_hora_turno = datetime.combine(
        horario.fecha,
        horario.hora
    ).replace(tzinfo=ZONA)

    ahora = datetime.now(tz=ZONA)

    if fecha_hora_turno <= ahora:
        raise HTTPException(
            status_code=400,
            detail="No se pueden reservar fechas pasadas"
        )

    # 5️⃣ Validar servicio activo
    servicio = (
        db.query(Servicio)
        .filter(
            Servicio.id == data.servicio_id,
            Servicio.activo == True
        )
        .first()
    )

    if not servicio:
        raise HTTPException(status_code=400, detail="Servicio inválido")

    # 6️⃣ Crear turno
    turno = Turno(
        nombre=usuario.nombre,
        telefono=data.telefono,
        horario_id=horario.id,
        usuario_id=usuario.id,
        servicio_id=servicio.id,
        precio=servicio.precio,
        barbero_id=horario.barbero_id
    )

    horario.disponible = False

    db.add(turno)
    db.commit()
    db.refresh(turno)

    # 7️⃣ Obtener nombre del barbero (sin query extra si hay relación)
    barbero_nombre = horario.barbero.nombre

    # 8️⃣ Enviar email
    try:
        enviar_email_confirmacion(
            destino=usuario.email,
            nombre=usuario.nombre,
            fecha=horario.fecha.strftime("%d/%m/%Y"),
            hora=horario.hora.strftime("%H:%M"),
            servicio=servicio.nombre,
            precio=servicio.precio,
            barbero=barbero_nombre
        )
    except Exception as e:
        print("⚠️ Error enviando email:", e)

    return {
        "ok": True,
        "mensaje": "Turno reservado y enviado por email",
        "turno_id": turno.id,
    }

@router.get("/profesionales")
def obtener_profesionales(db: Session = Depends(get_db)):
    profesionales = db.query(Usuario).filter(
        Usuario.rol.in_([RolEnum.barbero, RolEnum.admin])
    ).all()

    return [
        {
            "id": p.id,
            "nombre": p.nombre
        }
        for p in profesionales
    ] 

# --------------------------------------------------
# RUTA TEMPORAL: LIMPIAR HORARIOS 14:00
# --------------------------------------------------
@router.post("/limpiar-14")
def limpiar_14(db: Session = Depends(get_db)):
    """
    Elimina todos los horarios futuros libres a las 14:00.
    ⚠️ No toca turnos ya reservados.
    Usar solo una vez y luego borrar esta ruta.
    """
    from datetime import date, time

    eliminados = db.query(Horario).filter(
        Horario.fecha >= date.today(),  # Solo fechas futuras
        Horario.hora == time(14, 0),    # Solo 14:00
        Horario.disponible == True       # Solo horarios libres
    ).delete(synchronize_session=False)

    db.commit()

    return {"ok": True, "mensaje": f"Se eliminaron {eliminados} horarios de 14:00"}