"""FastAPI 入口：挂载看板、meta 与 v1 路由。"""
from __future__ import annotations
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from . import state
from .routes_meta import router as meta_router
from .routes_v1 import router as v1_router

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX = BASE_DIR / "app" / "static" / "index.html"
DOWNLOAD_DIR = BASE_DIR / "downloads"

app = FastAPI(title="免费 API 统一网关", version="1.0.0")
app.include_router(meta_router)
app.include_router(v1_router)


@app.on_event("startup")
async def _startup():
    state.init_state(DOWNLOAD_DIR)


@app.get("/")
async def index():
    return FileResponse(INDEX)


@app.get("/health")
async def health():
    return {"ok": True, "models": len(state.MODELS)}
