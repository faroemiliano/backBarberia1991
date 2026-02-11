# from datetime import date, time, datetime, timedelta
# from database import SesionLocal
# from models import Horario, HorarioBase

# # ========================
# # UTILIDADES
# # ========================

# DIAS = {
#     "monday": "lunes",
#     "tuesday": "martes",
#     "wednesday": "miercoles",
#     "thursday": "jueves",
#     "friday": "viernes",
#     "saturday": "sabado",
#     "sunday": "domingo",
# }

# def dia_espanol(fecha: date):
#     return DIAS[fecha.strftime("%A").lower()]

# # ========================
# # CONFIGURACIÓN
# # ========================

# db = SesionLocal()

# inicio = time(10, 0)
# fin = time(20, 0)
# intervalo = 30

# dias_abiertos = ["martes", "miercoles", "jueves", "viernes", "sabado"]

# # ========================
# # CARGAR HORARIOS BASE
# # ========================

# for dia in dias_abiertos:
#     hora = inicio
#     while hora < fin:
#         existe = db.query(HorarioBase).filter_by(dia_semana=dia, hora=hora).first()
#         if not existe:
#             db.add(HorarioBase(dia_semana=dia, hora=hora))
#         hora = (datetime.combine(date.today(), hora) + timedelta(minutes=intervalo)).time()

# db.commit()

# # ========================
# # GENERAR CALENDARIO (12 MESES)
# # ========================

# hoy = date.today()

# for i in range(365):   # 1 año completo
#     fecha = hoy + timedelta(days=i)
#     dia = dia_espanol(fecha)

#     for base in db.query(HorarioBase).filter_by(dia_semana=dia).all():
#         existe = db.query(Horario).filter_by(fecha=fecha, hora=base.hora).first()
#         if not existe:
#             db.add(Horario(fecha=fecha, hora=base.hora))

# db.commit()
# db.close()

# print("Agenda generada correctamente")
