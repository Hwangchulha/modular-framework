from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Web UI", version="1.0.0")
app.mount("/", StaticFiles(directory="ui_web/static", html=True), name="static")
