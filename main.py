from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from App.routers import router
from App.Database_Setup import Base, engine
from App.Models import User, RefreshToken, Address  # noqa: F401 - ensure models are registered

# Database schema migrations are now handled by Alembic: `alembic upgrade head`
# Base.metadata.create_all(bind=engine)

app = FastAPI(title="ShopCore API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
