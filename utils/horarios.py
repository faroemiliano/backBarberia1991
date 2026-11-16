from datetime import date, timedelta
from sqlalchemy.orm import Session
from models import Usuario, Horario, RolEnum
from services.agenda_service import horarios_para_barbero

INTERVALO = 40  # minutos

DIAS = {
    "monday": "lunes",
    "tuesday": "martes",
    "wednesday": "miercoles",
    "thursday": "jueves",
    "friday": "viernes",
    "saturday": "sabado",
    "sunday": "domingo",
}

def dia_espanol(fecha: date):
    return DIAS[fecha.strftime("%A").lower()]

def generar_horarios_barbero(db: Session, barbero: Usuario, dias_a_generar: int = 365):
    """
    Genera horarios disponibles para un barbero usando HorarioBase.
    """
    hoy = date.today()
    for i in range(dias_a_generar):
        fecha = hoy + timedelta(days=i)
        for hora in horarios_para_barbero(fecha, barbero):
            exists = db.query(Horario).filter_by(
                fecha=fecha, hora=hora, barbero_id=barbero.id
            ).first()
            if not exists:
                db.add(Horario(
                    fecha=fecha,
                    hora=hora,
                    disponible=True,
                    barbero_id=barbero.id
                ))
    db.commit()


def reconstruir_horarios_disponibles_barbero(
    db: Session,
    barbero: Usuario,
    dias_a_generar: int = 365,
):
    """Deja la agenda pública del profesional en la grilla vigente.

    Conserva turnos ocupados y bloques manuales, y reemplaza solo los slots
    futuros que estaban disponibles.
    """
    hoy = date.today()
    db.query(Horario).filter(
        Horario.barbero_id == barbero.id,
        Horario.fecha >= hoy,
        Horario.disponible.is_(True),
    ).delete(synchronize_session=False)

    horarios_conservados = {
        (fecha, hora)
        for fecha, hora in db.query(Horario.fecha, Horario.hora)
        .filter(
            Horario.barbero_id == barbero.id,
            Horario.fecha >= hoy,
        )
        .all()
    }

    for i in range(dias_a_generar):
        fecha = hoy + timedelta(days=i)
        for hora in horarios_para_barbero(fecha, barbero):
            if (fecha, hora) in horarios_conservados:
                continue
            db.add(Horario(
                fecha=fecha,
                hora=hora,
                disponible=True,
                barbero_id=barbero.id,
            ))

    db.commit()
