from database import engine
from models import Base

# IMPORTANTE: importar los modelos
import models  

Base.metadata.create_all(bind=engine)