import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


def enviar_email(destino, asunto, texto, html=None):
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        raise Exception("Configuración SMTP incompleta")

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_USER
    msg["To"] = destino
    msg["Subject"] = asunto

    msg.attach(MIMEText(texto, "plain", "utf-8"))

    if html:
        msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


# ----------------------------------
# CONFIRMACIÓN
# ----------------------------------
def enviar_email_confirmacion(destino, nombre, fecha, hora, servicio):
    texto = f"""
Hola {nombre},

Gracias por reservar tu turno 🙌

📅 Día: {fecha}
⏰ Horario: {hora}
✂️ Servicio: {servicio}

Te esperamos 💈
"""

    html = f"""
<html>
  <body style="font-family: Arial; color: #222;">
    <h2>¡Gracias por tu reserva! 🙌</h2>

    <p>Tu turno fue confirmado correctamente.</p>

    <ul>
      <li><strong>📅 Día:</strong> {fecha}</li>
      <li><strong>⏰ Horario:</strong> {hora}</li>
      <li><strong>✂️ Servicio:</strong> {servicio}</li>
    </ul>

    <p style="margin-top:20px;">¡Te esperamos!</p>
    <p>💈 Barbería</p>
  </body>
</html>
"""

    enviar_email(
        destino=destino,
        asunto="✅ Confirmación de tu turno",
        texto=texto,
        html=html
    )


# ----------------------------------
# CANCELACIÓN
# ----------------------------------
def enviar_email_cancelacion(destino, nombre, fecha, hora, servicio):
    texto = f"""
Hola {nombre},

Tu turno fue cancelado ❌

📅 Fecha: {fecha.strftime('%d/%m/%Y')}
⏰ Hora: {hora.strftime('%H:%M')}
✂️ Servicio: {servicio}

Si necesitás reprogramar, podés hacerlo desde la web.

Saludos,
Barbería 💈
"""

    enviar_email(
        destino=destino,
        asunto="❌ Turno cancelado – Barbería",
        texto=texto
    )


# ----------------------------------
# EDICIÓN
# ----------------------------------
def enviar_email_edicion(
    destino,
    nombre,
    fecha_anterior,
    hora_anterior,
    fecha_nueva,
    hora_nueva,
    servicio_anterior,
    servicio_nuevo
):
    texto = f"""
Hola {nombre},

Tu turno fue modificado correctamente.

Antes:
📅 {fecha_anterior.strftime('%d/%m/%Y')}
⏰ {hora_anterior.strftime('%H:%M')}
✂️ {servicio_anterior}

Ahora:
📅 {fecha_nueva.strftime('%d/%m/%Y')}
⏰ {hora_nueva.strftime('%H:%M')}
✂️ {servicio_nuevo}

Si tenés alguna consulta, comunicate con la barbería.

Saludos,
Barbería 💈
"""

    enviar_email(
        destino=destino,
        asunto="✏️ Tu turno fue modificado",
        texto=texto
    )
