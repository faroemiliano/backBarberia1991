from fastapi import APIRouter, HTTPException, Depends
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.orm import Session
from database import SesionLocal
from models import Usuario
from auth.security import create_token
from database import get_db

import os

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")


print("GOOGLE_CLIENT_ID:", GOOGLE_CLIENT_ID)
@router.post("/auth/google")
def login_google(payload: dict, db: Session = Depends(get_db)):
    try:
        token = payload["credential"]

        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )

        email = idinfo["email"]
        nombre = idinfo.get("name", "")

        user = db.query(Usuario).filter_by(email=email).first()

        if not user:
            user = Usuario(
                nombre=nombre,
                email=email,
                is_admin=email == ADMIN_EMAIL
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        jwt = create_token({
            "sub": str(user.id),
            "is_admin": user.is_admin
        })

        return {
            "access_token": jwt,
            "user": {
                "id": user.id,
                "nombre": user.nombre,
                "email": user.email,
                "is_admin": user.is_admin
            }
        }

    except Exception as e:
        print("ERROR GOOGLE AUTH:", e)
        raise HTTPException(status_code=401, detail="Login con Google inválido")
