from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
load_dotenv()
print(os.getenv("ADMIN_EMAIL"))
from database import engine
from models import Base

from routers import auth, calendario, admin, auth_google, admin_servicios


app = FastAPI(title="Barbería API")

# =====================
# BASE DE DATOS 
# =====================
Base.metadata.create_all(bind=engine)

# =====================
# CORS
# =====================
app.add_middleware(
    CORSMiddleware,
   allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://front-barberia1991.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# ROUTERS
# =====================
app.include_router(auth.router, prefix="", tags=["Auth"])
app.include_router(calendario.router, prefix="", tags=["Calendario"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(auth_google.router)
app.include_router(admin_servicios.router)
