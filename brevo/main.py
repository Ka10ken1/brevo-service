from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .router import router

app = FastAPI(title="Brevo Background Service")


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_logs():
    return FileResponse("static/index.html")


app.include_router(router)
