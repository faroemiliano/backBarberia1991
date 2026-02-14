from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import SesionLocal
from models import Horario, Turno, Usuario, Servicio
from auth.security import decode_token
from pydantic import BaseModel, Field
from datetime import date, timedelta, time
import calendar
from datetime import datetime
from database import get_db


from utils.email import enviar_email_confirmacion

router = APIRouter()



class SolicitudTurno(BaseModel):
    telefono: str = Field(..., min_length=8, max_length=20)
    servicio_id: int
    horario_id: int

# --------------------------------------------------
# OBTENER TODO EL CALENDARIO
# --------------------------------------------------
@router.get("/calendario")
def calendario(db: Session = Depends(get_db)):
    hoy = date.today()

    horarios = (
        db.query(Horario)
        .filter(
            Horario.disponible == True,
            Horario.fecha >= hoy
        )
        .order_by(Horario.fecha, Horario.hora)
        .all()
    )

    return horarios
# --------------------------------------------------
# GENERAR TODO EL AÑO (UNA SOLA VEZ)
# --------------------------------------------------
@router.post("/preparar-calendario")
def preparar_calendario(db: Session = Depends(get_db)):

    anio = date.today().year
    inicio = date(anio, 1, 1)
    fin = date(anio, 12, 31)

    HORAS = [
        time(h, m)
        for h in range(9, 20)
        for m in (0, 30)
    ] + [time(20, 0)]

    actual = inicio
    creados = 0

    while actual <= fin:

        # ✅ SOLO MARTES (1) A SÁBADO (5)
        if actual.weekday() in {1, 2, 3, 4, 5}:
            for hora in HORAS:
                existe = db.query(Horario).filter_by(
                    fecha=actual,
                    hora=hora
                ).first()

                if not existe:
                    db.add(Horario(
                        fecha=actual,
                        hora=hora,
                        disponible=True
                    ))
                    creados += 1

        actual += timedelta(days=1)

    db.commit()
    return {"ok": True, "horarios_creados": creados}

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
@router.post("/reservar")
def reservar(
    data: SolicitudTurno,
    db: Session = Depends(get_db),
    authorization: str = Header(...)
):
    # 1️⃣ Validar header Authorization
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token mal formado")

    token = authorization.replace("Bearer ", "").strip()

    # 2️⃣ Decodificar token
    payload = decode_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    # 3️⃣ Usuario
    usuario = db.query(Usuario).filter_by(id=user_id).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    # 4️⃣ Horario disponible
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

    # 5️⃣ Fecha pasada
    fecha_hora = datetime.combine(horario.fecha, horario.hora)
    if fecha_hora < datetime.now():
        raise HTTPException(
            status_code=400,
            detail="No se pueden reservar fechas pasadas"
        )

    # 6️⃣ Servicio válido
    servicio = db.query(Servicio).filter(
        Servicio.id == data.servicio_id,
        Servicio.activo == True
    ).first()

    if not servicio:
        raise HTTPException(status_code=400, detail="Servicio inválido")

    turno = Turno(
        nombre=usuario.nombre,
        telefono=data.telefono,
        horario_id=horario.id,
        usuario_id=usuario.id,
        servicio_id=servicio.id,
        precio=servicio.precio
    )

    horario.disponible = False
    db.add(turno)
    db.commit()
    db.refresh(turno)

    # 8️⃣ Email
    try:
        enviar_email_confirmacion(
            destino=usuario.email,
            nombre=usuario.nombre,
            fecha=horario.fecha.strftime("%d/%m/%Y"),
            hora=horario.hora.strftime("%H:%M"),
            servicio=servicio.nombre
    )
    except Exception as e:
        print("⚠️ Error enviando email:", e)

    return {
        "ok": True,
        "mensaje": "Turno reservado y enviado por email",
        "turno_id": turno.id,
    }

