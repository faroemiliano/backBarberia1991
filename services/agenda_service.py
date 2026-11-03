from datetime import date, datetime, time, timedelta
from sqlalchemy.dialects.postgresql import insert
from models import Horario, HorarioBase, RolEnum, Usuario
from database import SesionLocal

DIAS = {
    "monday": "lunes",
    "tuesday": "martes",
    "wednesday": "miercoles",
    "thursday": "jueves",
    "friday": "viernes",
    "saturday": "sabado",
    "sunday": "domingo",
}

FRANJAS = {
    "martes":   [(time(11,0), time(14,0)), (time(15,0), time(20,0))],
    "miercoles":[(time(11,0), time(14,0)), (time(15,0), time(20,0))],
    "jueves":   [(time(11,0), time(14,0)), (time(15,0), time(20,0))],
    "viernes":  [(time(10,0), time(14,0)), (time(15,0), time(20,0))],
    "sabado":   [(time(10,0), time(14,0)), (time(15,0), time(20,0))],
}

INTERVALO = 40

def dia_espanol(fecha: date):
    return DIAS[fecha.strftime("%A").lower()]


def horarios_base_esperados():
    horarios = []
    for dia, franjas in FRANJAS.items():
        for inicio, fin in franjas:
            hora_actual = inicio
            while hora_actual < fin:
                horarios.append((dia, hora_actual))
                hora_actual = (
                    datetime.combine(date.today(), hora_actual)
                    + timedelta(minutes=INTERVALO)
                ).time()
    return horarios


def normalizar_agenda_a_40_minutos():
    """Migra una agenda previa de 30 minutos sin tocar turnos ni bloqueos."""
    db = SesionLocal()
    try:
        esperados = set(horarios_base_esperados())
        actuales = {
            (base.dia_semana, base.hora)
            for base in db.query(HorarioBase).all()
        }

        if actuales == esperados:
            return

        hoy = date.today()

        # Solo se reemplazan slots futuros disponibles. Los ocupados y los
        # bloqueados manualmente permanecen intactos.
        db.query(Horario).filter(
            Horario.fecha >= hoy,
            Horario.disponible.is_(True),
        ).delete(synchronize_session=False)

        db.query(HorarioBase).delete(synchronize_session=False)
        db.add_all(
            HorarioBase(dia_semana=dia, hora=hora)
            for dia, hora in horarios_base_esperados()
        )
        db.commit()

        barberos = db.query(Usuario).filter(
            Usuario.rol.in_([RolEnum.barbero, RolEnum.admin])
        ).all()
        bases_por_dia = {}
        for base in db.query(HorarioBase).all():
            bases_por_dia.setdefault(base.dia_semana, []).append(base)

        nuevos = []
        for barbero in barberos:
            for i in range(365):
                fecha = hoy + timedelta(days=i)
                for base in bases_por_dia.get(dia_espanol(fecha), []):
                    nuevos.append({
                        "fecha": fecha,
                        "hora": base.hora,
                        "disponible": True,
                        "barbero_id": barbero.id,
                    })

        if nuevos:
            stmt = insert(Horario).values(nuevos)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["fecha", "hora", "barbero_id"]
            )
            db.execute(stmt)
            db.commit()
    finally:
        db.close()


def generar_agenda_si_vacia():
    db = SesionLocal()

    # 🔎 Si ya hay horarios, no hacemos nada
    if db.query(Horario).first():
        print("⏭️ Agenda ya existente, no se genera nada")
        db.close()
        return

    print("🚀 Generando agenda automática...")

    # 1️⃣ Horarios base
    for dia, hora in horarios_base_esperados():
        exists = db.query(HorarioBase).filter_by(
            dia_semana=dia,
            hora=hora,
        ).first()
        if not exists:
            db.add(HorarioBase(dia_semana=dia, hora=hora))

    db.commit()

    # 2️⃣ Horarios reales
    hoy = date.today()

    barberos = db.query(Usuario).filter(
        Usuario.rol.in_([RolEnum.barbero, RolEnum.admin])
    ).all()

    bases = db.query(HorarioBase).all()

    bases_por_dia = {}
    for base in bases:
        bases_por_dia.setdefault(base.dia_semana, []).append(base)

    nuevos = []

    for barbero in barberos:
        for i in range(365):
            fecha = hoy + timedelta(days=i)
            dia = dia_espanol(fecha)

            for base in bases_por_dia.get(dia, []):
                nuevos.append({
                    "fecha": fecha,
                    "hora": base.hora,
                    "disponible": True,
                    "barbero_id": barbero.id
                })

    stmt = insert(Horario).values(nuevos)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["fecha", "hora", "barbero_id"]
    )

    db.execute(stmt)
    db.commit()
    db.close()

    print("✅ Agenda generada automáticamente")
