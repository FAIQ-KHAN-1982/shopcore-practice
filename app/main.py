from fastapi import FastAPI
from app.routers import auth
from app.database import Base, engine

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)