from fastapi import FastAPI
from .router import router

app = FastAPI(title="Brevo API Service")

app.include_router(router)
