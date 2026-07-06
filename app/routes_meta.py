"""看板数据接口：status / logs / tasks。前端 index.html 每 3 秒轮询一次。"""
from __future__ import annotations
from fastapi import APIRouter

from . import state

router = APIRouter()


@router.get("/api/status")
async def api_status():
    return {"strategy": state.STRATEGY, "models": state.list_models()}


@router.get("/api/logs")
async def api_logs():
    return {"logs": state.recent_logs()}


@router.get("/api/tasks")
async def api_tasks():
    return {"tasks": state.list_tasks()}
