import sys
import os
from dotenv import load_dotenv  # <-- agregar esto
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
load_dotenv()  # <-- esto lee tu .env
from datetime import date, datetime, time, timedelta
from database import SesionLocal
from models import Horario, HorarioBase, RolEnum, Turno, Usuario

# ========================
# CONFIG
# ========================

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

FRANJAS = {
    "martes":   [(time(11,0), time(14,0)), (time(15,0), time(20,0))],
    "miercoles":[(time(11,0), time(14,0)), (time(15,0), time(20,0))],
    "jueves":   [(time(11,0), time(14,0)), (time(15,0), time(20,0))],
    "viernes":  [(time(10,0), time(14,0)), (time(15,0), time(20,0))],
    "sabado":   [(time(10,0), time(14,0)), (time(15,0), time(20,0))],
}

INTERVALO = 30

db = SesionLocal()

# ========================
# 0️⃣ BORRAR TODO
# ========================

print("🗑 Borrando turnos y horarios antiguos...")
db.query(Turno).delete()
db.query(Horario).delete()
db.query(HorarioBase).delete()
db.commit()

# ========================
# 1️⃣ GENERAR HORARIOS BASE
# ========================

print("📅 Generando horarios base...")

for dia, franjas in FRANJAS.items():
    for inicio, fin in franjas:
        hora_actual = inicio

        while hora_actual < fin:
            db.add(HorarioBase(
                dia_semana=dia,
                hora=hora_actual
            ))

            hora_actual = (
                datetime.combine(date.today(), hora_actual)
                + timedelta(minutes=INTERVALO)
            ).time()

db.commit()

# ========================
# 2️⃣ GENERAR HORARIOS POR BARBERO (1 AÑO)
# ========================

print("⏳ Generando horarios reales por barbero...")

hoy = date.today()

# 🔥 SOLO usuarios con rol barbero
barberos = db.query(Usuario).filter(
    Usuario.rol == RolEnum.barbero
).all()

for barbero in barberos:
    for i in range(365):
        fecha = hoy + timedelta(days=i)
        dia = dia_espanol(fecha)

        bases = db.query(HorarioBase).filter_by(
            dia_semana=dia
        ).all()

        for base in bases:
            db.add(Horario(
                fecha=fecha,
                hora=base.hora,
                disponible=True,
                barbero_id=barbero.id  # 🔥 CLAVE
            ))

db.commit()
db.close()

print("✅ Agenda generada correctamente para todos los barberos")