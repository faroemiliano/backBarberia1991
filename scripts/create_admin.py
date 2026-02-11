from database import SesionLocal
from models import Usuario

db = SesionLocal()

user = db.query(Usuario).filter(Usuario.email == "faroemiliano@gmail.com").first()

if not user:
    print("❌ Usuario no encontrado")
else:
    user.is_admin = True
    db.commit()
    print("✅ Usuario marcado como ADMIN correctamente")