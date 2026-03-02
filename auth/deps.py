from fastapi import Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session

from auth.security import SECRET_KEY, ALGORITHM, decode_token
from database import get_db
from models import RolEnum, Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# 🔐 Obtener usuario actual
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")

        user = db.query(Usuario).filter_by(id=int(user_id)).first()

        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")

        return user

    except:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")


# 👑 Admin
def admin_required(
    user: Usuario = Depends(get_current_user)
):
    if user.rol != RolEnum.admin:
        raise HTTPException(status_code=403, detail="No autorizado")
    return user


# 💈 Barbero
def barbero_required(
    db: Session = Depends(get_db),
    authorization: str = Header(...)
):
    token = authorization.replace("Bearer ", "").strip()
    payload = decode_token(token)

    user_id = payload.get("sub")  # ✅ CORRECTO

    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = db.query(Usuario).filter_by(id=int(user_id)).first()

    if not user or user.rol != RolEnum.barbero:
        raise HTTPException(status_code=403, detail="No autorizado")

    return user