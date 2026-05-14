from fastapi import APIRouter
from pydantic import BaseModel

import os
import resend

router = APIRouter()

resend.api_key = os.getenv("RESEND_API_KEY")

class ContactForm(BaseModel):
    nombre: str
    email: str
    mensaje: str

@router.post("/contact")
def contact(data: ContactForm):

    try:
        resend.Emails.send({
            "from": "Farixio <contacto@farixio.com>",
            "to": ["faroemilianotech@gmail.com"],
            "subject": "Nuevo contacto desde Farixio",
            "html": f"""
                <h2>Nuevo contacto</h2>

                <p>
                    <strong>Nombre:</strong>
                    {data.nombre}
                </p>

                <p>
                    <strong>Email:</strong>
                    {data.email}
                </p>

                <p>
                    <strong>Mensaje:</strong>
                    {data.mensaje}
                </p>
            """
        })

        return {
            "success": True,
            "message": "Email enviado"
        }

    except Exception as e:
        print(e)

        return {
            "success": False,
            "message": "Error enviando email"
        }