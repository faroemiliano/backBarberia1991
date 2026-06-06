# routers/turnos_usuario.py
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session, joinedload
from auth.deps import get_current_user
from database import get_db
from models import Turno, Usuario, Horario, Servicio
from auth.security import decode_token
from datetime import datetime
from utils.email import enviar_email_cancelacion

router = APIRouter()


# --------------------------------------------------
# OBTENER TURNOS DEL USUARIO LOGUEADO
# --------------------------------------------------
@router.get("/mis-turnos")
def mis_turnos(
    db: Session = Depends(get_db),
    authorization: str = Header(...)
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token mal formado")

    token = authorization.replace("Bearer ", "").strip()
    payload = decode_token(token)
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    turnos = (
        db.query(Turno)
        .join(Horario)
        .join(Servicio)
        .filter(Turno.usuario_id == user_id)
        .order_by(Horario.fecha, Horario.hora)
        .all()
    )

    return [
        {
            "id": t.id,
            "servicio": t.servicio.nombre,
            "precio": t.precio,
            "fecha": t.horario.fecha,
            "hora": t.horario.hora.strftime("%H:%M"),
            "barbero": t.barbero.nombre,
        }
        for t in turnos
    ]


# --------------------------------------------------
# CANCELAR TURNO
# --------------------------------------------------
@router.delete("/cancelar-turno/{turno_id}")
def cancelar_turno(
    turno_id: int,
    db: Session = Depends(get_db),
    authorization: str = Header(...)
):
    # 🔐 AUTH
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token mal formado")

    token = authorization.replace("Bearer ", "").strip()
    payload = decode_token(token)
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    # 🔥 TRAER CON USUARIO (CLAVE)
    turno = (
        db.query(Turno)
        .options(joinedload(Turno.usuario))
        .filter(
            Turno.id == turno_id,
            Turno.usuario_id == user_id
        )
        .first()
    )

    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    # ⏱ VALIDAR FECHA
    fecha_hora = datetime.combine(
        turno.horario.fecha,
        turno.horario.hora
    )

    if fecha_hora < datetime.now():
        raise HTTPException(
            status_code=400,
            detail="No se pueden cancelar turnos pasados"
        )

    # 📧 DEBUG
    print("👤 USUARIO:", turno.usuario)
    print("📧 EMAIL:", turno.usuario.email if turno.usuario else None)

    # 📧 ENVIAR EMAIL (ANTES DE BORRAR)
    try:
        if turno.usuario and turno.usuario.email:
            enviar_email_cancelacion(
                destino=turno.usuario.email,
                nombre=turno.usuario.nombre,
                fecha=turno.horario.fecha,
                hora=turno.horario.hora,
                servicio=turno.servicio.nombre,
            )
            print("✅ Email cancelación enviado")
        else:
            print("⚠️ Usuario sin email")
    except Exception as e:
        print("❌ Error enviando email:", e)

    # 🔓 LIBERAR HORARIO
    turno.horario.disponible = True

    # 🗑 ELIMINAR
    db.delete(turno)
    db.commit()

    return {"ok": True, "mensaje": "Turno cancelado"}

