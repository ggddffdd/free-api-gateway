"""统一入口：/v1/chat、/v1/image、/v1/video。

网关即"多步决策 Agent"：识别任务 -> 过滤可用模型 -> 结合额度与策略选优 -> 调用 -> 记账 -> 出日志。
"""
from __future__ import annotations
import asyncio

from fastapi import APIRouter, HTTPException

from . import state, router as routing
from .adapters import get_adapter, AgnesAdapter

router = APIRouter()


async def _dispatch(task_type: str, prompt: str, strategy: str | None, model_hint: str | None):
    model = None
    if model_hint and (m := state.get_model(model_hint)):
        if task_type in m["supports"]:
            model = m
    if model is None:
        model = routing.select_model(task_type, strategy)
    if model is None:
        raise HTTPException(503, f"没有可用模型支持 {task_type}")

    adapter = get_adapter(model)
    res = await adapter.call(task_type, prompt)
    await state.consume_quota(model["id"], res.get("cost", model["cost"]))
    await state.add_log(model["display"], task_type, res.get("cost", model["cost"]), res.get("mock", True), res.get("ok", False))
    return {"model": model["display"], "mode": model["mode"], "mock": res.get("mock", True),
            "cost": res.get("cost", model["cost"]), "content": res.get("content"), "ok": res.get("ok", True)}


@router.post("/v1/chat")
async def chat(body: dict):
    prompt = body.get("prompt", "")
    strategy = body.get("strategy")
    model_hint = body.get("model")
    return await _dispatch("chat", prompt, strategy, model_hint)


@router.post("/v1/image")
async def image(body: dict):
    prompt = body.get("prompt", "")
    strategy = body.get("strategy")
    model_hint = body.get("model")
    return await _dispatch("image", prompt, strategy, model_hint)


@router.post("/v1/video")
async def video(body: dict):
    prompt = body.get("prompt", "")
    duration = int(body.get("duration", 5))
    model_hint = body.get("model")
    model = None
    if model_hint and (m := state.get_model(model_hint)):
        if "video" in m["supports"]:
            model = m
    if model is None:
        model = routing.select_model("video")
    if model is None:
        raise HTTPException(503, "没有可用模型支持 video")

    tid = await state.new_task(model["id"], prompt, duration)
    asyncio.create_task(_run_video(tid, model, prompt, duration))
    return {"task_id": tid, "model": model["display"], "status": "pending"}


@router.get("/v1/video/{task_id}")
async def video_status(task_id: str):
    t = state.get_task(task_id)
    if not t:
        raise HTTPException(404, "task not found")
    return t


async def _run_video(tid: str, model: dict, prompt: str, duration: int):
    # Agnes 真实视频路径：提交 -> 实时轮询 -> 下载落地（状态实时回写看板）
    if model["id"] == "agnes" and model["mode"] == "real" and model.get("api_key"):
        adapter = AgnesAdapter(model)
        await state.update_task(tid, status="submitted", progress=0)
        try:
            agnes_tid = await adapter.video_submit(prompt, duration)
        except Exception as e:  # noqa: BLE001
            await state.update_task(tid, status="failed", progress=0, error=f"提交失败: {e}")
            await state.consume_quota(model["id"], model["cost"])
            await state.add_log(model["display"], "video", model["cost"], False, False)
            return

        progress = 0
        done = False
        for _ in range(120):  # 最多 ~20 分钟
            await asyncio.sleep(10)
            progress = min(95, progress + 1)
            try:
                status, url = await adapter.video_poll(agnes_tid)
            except Exception:  # noqa: BLE001
                status, url = None, ""
            if status == "completed" and url:
                local = await adapter.video_download(url, state.DOWNLOAD_DIR, agnes_tid)
                await state.update_task(tid, status="done", progress=100, result={"downloaded_to": local, "url": url})
                done = True
                break
            if status in ("failed", "error"):
                await state.update_task(tid, status="failed", progress=progress, error="Agnes 生成失败")
                break
            mapped = {"queued": "queued", "processing": "processing"}.get(status or "", "processing")
            await state.update_task(tid, status=mapped, progress=progress)

        if not done and status not in ("failed", "error"):
            await state.update_task(tid, status="failed", progress=progress, error="轮询超时（>20分钟）")

        await state.consume_quota(model["id"], model["cost"])
        await state.add_log(model["display"], "video", model["cost"], False, done)
        return

    # 其余模型走 Mock 模拟（含未配置 key 的 Agnes）
    await state.update_task(tid, status="running", progress=0)
    steps = max(1, duration)
    for i in range(1, steps + 1):
        await asyncio.sleep(1)
        await state.update_task(tid, progress=min(100, int(i / steps * 100)))
    fname = f"{tid}.mp4"
    path = state.DOWNLOAD_DIR / fname
    try:
        path.write_text(f"MOCK VIDEO\nprompt: {prompt}\nduration: {duration}s\n")
    except Exception:
        pass
    await state.consume_quota(model["id"], model["cost"])
    await state.add_log(model["display"], "video", model["cost"], model["mode"] != "real", True)
    await state.update_task(tid, status="done", progress=100,
                            result={"downloaded_to": str(path)})
