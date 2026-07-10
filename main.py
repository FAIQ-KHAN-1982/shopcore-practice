from fastapi import FastAPI
from App.routers import router

app = FastAPI(title="ShopCore API")
app.include_router(router)
