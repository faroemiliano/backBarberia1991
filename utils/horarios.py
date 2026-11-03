from datetime import date, timedelta
from sqlalchemy.orm import Session
from models import Usuario, Horario, RolEnum
from services.agenda_service import horarios_para_fecha

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
        for hora in horarios_para_fecha(fecha):
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
