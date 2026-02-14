from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
load_dotenv()
print(os.getenv("ADMIN_EMAIL"))
from database import engine
from models import Base

from routers import auth, calendario, admin, auth_google, admin_servicios


app = FastAPI(title="Barbería API")

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Barberia API",
        version="1.0",
        description="API de turnos",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

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
