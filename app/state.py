"""全局运行时状态：模型注册表、额度计数、路由日志、异步视频任务。

说明：挑战赛演示与单机运行场景下，进程内内存状态足够。
若需多进程/重启持久化，可后续替换为 Redis 或 sqlite。
"""
from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from .config import load_config

STRATEGY = "cost"

MODELS: dict[str, dict] = {}

LOGS: list[dict] = []
LOG_LOCK = asyncio.Lock()

TASKS: dict[str, dict] = {}
TASK_LOCK = asyncio.Lock()

DOWNLOAD_DIR = None  # 由 main 启动时设置


def _now() -> str:
    return time.strftime("%H:%M:%S", time.localtime())


def init_state(download_dir) -> None:
    global STRATEGY, MODELS, DOWNLOAD_DIR
    cfg = load_config()
    STRATEGY = cfg.get("strategy", "cost")
    DOWNLOAD_DIR = download_dir
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    MODELS.clear()
    for mid, m in (cfg.get("models") or {}).items():
        MODELS[mid] = {
            "id": mid,
            "display": m.get("display", mid),
            "enabled": bool(m.get("enabled", True)),
            "mode": m.get("mode", "mock"),
            "supports": m.get("supports", []),
            "api_key": m.get("api_key", ""),
            "api_model": m.get("api_model", ""),
            "api_model_image": m.get("api_model_image", ""),
            "endpoint": m.get("endpoint", ""),
            "daily_limit": int(m.get("daily_limit", 100)),
            "used": 0,
            "quality": int(m.get("quality", 60)),
            "speed": int(m.get("speed", 60)),
            "cost": int(m.get("cost", 1)),
        }


def list_models() -> list[dict]:
    out = []
    for m in MODELS.values():
        remaining = max(0, m["daily_limit"] - m["used"])
        out.append({
            "id": m["id"],
            "display": m["display"],
            "enabled": m["enabled"],
            "mode": m["mode"],
            "supports": m["supports"],
            "used": m["used"],
            "daily_limit": m["daily_limit"],
            "remaining": remaining,
            "quality": m["quality"],
            "speed": m["speed"],
        })
    return out


def get_model(mid: str) -> Optional[dict]:
    return MODELS.get(mid)


async def add_log(model: str, task: str, cost: int, mock: bool, ok: bool) -> None:
    async with LOG_LOCK:
        LOGS.append({
            "time": _now(),
            "model": model,
            "task": task,
            "cost": cost,
            "mock": mock,
            "ok": ok,
        })


def recent_logs(limit: int = 50) -> list[dict]:
    return LOGS[-limit:]


async def consume_quota(mid: str, cost: int) -> None:
    m = MODELS.get(mid)
    if m:
        m["used"] = min(m["daily_limit"], m["used"] + cost)


async def new_task(mid: str, prompt: str, duration: int) -> str:
    import uuid
    tid = uuid.uuid4().hex[:12]
    async with TASK_LOCK:
        TASKS[tid] = {
            "task_id": tid,
            "model": mid,
            "prompt": prompt,
            "duration": duration,
            "status": "pending",
            "progress": 0,
            "result": None,
            "error": None,
            "created": _now(),
        }
    return tid


async def update_task(tid: str, **kw) -> None:
    async with TASK_LOCK:
        if tid in TASKS:
            TASKS[tid].update(kw)


def get_task(tid: str) -> Optional[dict]:
    return TASKS.get(tid)


def list_tasks() -> list[dict]:
    return list(TASKS.values())
