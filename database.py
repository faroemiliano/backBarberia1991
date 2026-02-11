from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

URL_BD = "postgresql://emilianofaro:postgres@localhost/barberia"

engine = create_engine(URL_BD)
SesionLocal = sessionmaker(bind=engine)

def get_db():
    db = SesionLocal()
    try:
        yield db
    finally:
        db.close()