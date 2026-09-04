import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from App.Routers import router
from App.Database_Setup import Base, engine
from App.Models import User, RefreshToken, Address  # noqa: F401 - ensure models are registered

# Database schema migrations are now handled by Alembic: `alembic upgrade head`
# Base.metadata.create_all(bind=engine)

app = FastAPI(title="ShopCore API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")

@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/app/")

