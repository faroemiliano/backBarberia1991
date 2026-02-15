import os
import resend


# =========================================================
# FUNCION BASE (segura, nunca rompe el servidor)
# =========================================================
# def enviar_email(destino, asunto, texto, html=None):

#     api_key = os.getenv("RESEND_API_KEY")

#     if not api_key:
#         print("⚠️ Email desactivado: RESEND_API_KEY no configurada")
#         return  # no rompe la app

#     try:
#         resend.api_key = api_key

#         contenido_html = html if html else f"<pre>{texto}</pre>"

#         resend.Emails.send({
#             "from": "Barberia <onboarding@resend.dev>",
#             "to": [destino],
#             "subject": asunto,
#             "html": contenido_html
#         })

#         print("✅ Email enviado correctamente")

#     except Exception as e:
#         # Nunca dejar que el email rompa la request principal
#         print("❌ Error enviando email:", str(e))
def enviar_email(destino, asunto, texto, html=None):

    if not resend.api_key:
        raise Exception("RESEND_API_KEY no configurada")

    EMAIL_TEST = os.getenv("EMAIL_TEST")

    if EMAIL_TEST:
        print(f"[TEST MODE] Email real: {destino} -> redirigido a {EMAIL_TEST}")
        destino = EMAIL_TEST
        from_email = f"Barberia <{EMAIL_TEST}>"
    else:
        from_email = "Barberia <onboarding@resend.dev>"

    contenido_html = html if html else f"<pre>{texto}</pre>"

    resend.Emails.send({
        "from": from_email,
        "to": [destino],
        "subject": asunto,
        "html": contenido_html
    })

# =========================================================
# CONFIRMACION
# =========================================================
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
<h2>¡Gracias por tu reserva! 🙌</h2>
<p>Tu turno fue confirmado correctamente.</p>

<ul>
<li><b>📅 Día:</b> {fecha}</li>
<li><b>⏰ Horario:</b> {hora}</li>
<li><b>✂️ Servicio:</b> {servicio}</li>
</ul>

<p>¡Te esperamos!</p>
<p>💈 Barbería</p>
"""

    enviar_email(destino, "✅ Confirmación de tu turno", texto, html)


# =========================================================
# CANCELACION
# =========================================================
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

    enviar_email(destino, "❌ Turno cancelado – Barbería", texto)


# =========================================================
# EDICION
# =========================================================
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

Saludos,
Barbería 💈
"""

    enviar_email(destino, "✏️ Tu turno fue modificado", texto)
