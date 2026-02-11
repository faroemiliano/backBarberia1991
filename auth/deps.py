from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from auth.security import SECRET_KEY, ALGORITHM
from database import SesionLocal
from models import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        db = SesionLocal()
        user = db.query(Usuario).filter_by(id=int(user_id)).first()
        db.close()

        if not user:
            raise HTTPException(401)
        return user
    except:
        raise HTTPException(401)

def admin_required(user: Usuario = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(403)
    return user
