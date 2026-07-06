"""适配器层：每个平台声明支持类型与单次成本，提供 call() 统一调用。

- MockAdapter：无需 key，返回拟真内容，全链路可演示。
- OpenAICompatibleAdapter：智谱/混元/硅基流动/魔搭 的 chat & image（OpenAI 兼容协议）。
- AgnesAdapter：chat / image 同步真实调用 + video 异步提交/轮询/下载（apihub.agnes-ai.com）。
真实调用需填入 api_key 且 mode=real；否则一律走 Mock。
"""
from __future__ import annotations
import asyncio
import httpx
import uuid
from . import state

MOCK_REPLIES = {
    "chat": "（Mock）这是来自网关的模拟回复。填入真实 api_key 后即可调用对应大模型。",
    "image": "https://placehold.co/600x400?text=Mock+Image",
    "video": "https://placehold.co/480x270?text=Mock+Video",
}


class Adapter:
    def __init__(self, model: dict):
        self.m = model

    async def call(self, task_type: str, prompt: str, **kw) -> dict:
        raise NotImplementedError


class MockAdapter(Adapter):
    async def call(self, task_type: str, prompt: str, **kw) -> dict:
        return {
            "content": MOCK_REPLIES.get(task_type, "（Mock）ok"),
            "cost": self.m["cost"],
            "mock": True,
            "ok": True,
        }


class OpenAICompatibleAdapter(Adapter):
    """智谱 / 混元 / 硅基流动 / 魔搭 的 chat 与 image（OpenAI 兼容）。

    真实模型名由 config 的 api_model 指定（如 glm-4-flash）；未配置时回退到内部 id。
    免费 API 偶发抖动，带重试兜底。
    """

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.m['api_key']}", "Content-Type": "application/json"}

    async def _request(self, url: str, payload: dict, timeout: int = 30, retries: int = 2) -> dict:
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    r = await client.post(url, json=payload, headers=self._headers())
                if r.status_code in (404, 429) or r.status_code >= 500:
                    last_exc = httpx.HTTPStatusError(f"HTTP {r.status_code}", request=r.request, response=r)
                    if attempt < retries:
                        await asyncio.sleep(2)
                        continue
                    r.raise_for_status()
                else:
                    r.raise_for_status()
                return r.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_exc = e
                if attempt < retries:
                    await asyncio.sleep(2)
                    continue
                raise
        assert last_exc is not None
        raise last_exc

    def _download_image(self, url: str) -> str:
        try:
            d = state.DOWNLOAD_DIR
            if not d:
                return url
            fname = f"{self.m['id']}_{uuid.uuid4().hex[:8]}.png"
            with httpx.Client(timeout=120) as c:
                r = c.get(url)
                r.raise_for_status()
                (d / fname).write_bytes(r.content)
            return str(d / fname)
        except Exception:  # noqa: BLE001
            return url

    async def call(self, task_type: str, prompt: str, **kw) -> dict:
        endpoint = self.m["endpoint"].rstrip("/")
        chat_model = self.m.get("api_model") or self.m["id"]
        img_model = self.m.get("api_model_image") or self.m.get("api_model") or self.m["id"]
        try:
            if task_type == "chat":
                payload = {"model": chat_model, "messages": [{"role": "user", "content": prompt}]}
                url = f"{endpoint}/chat/completions"
            elif task_type == "image":
                payload = {"model": img_model, "prompt": prompt, "n": 1, "size": "512x512"}
                url = f"{endpoint}/images/generations"
            else:
                return {"content": "", "cost": self.m["cost"], "mock": False, "ok": False}
            data = await self._request(url, payload, timeout=30)
            if task_type == "chat":
                content = data["choices"][0]["message"]["content"]
            else:
                # 兼容 OpenAI(data[].url) 与硅基流动(images[].url)
                if "data" in data and data.get("data"):
                    img_url = data["data"][0]["url"]
                elif "images" in data and data.get("images"):
                    img_url = data["images"][0]["url"]
                else:
                    raise ValueError(f"无法解析图像响应: {str(data)[:200]}")
                content = self._download_image(img_url)
            return {"content": content, "cost": self.m["cost"], "mock": False, "ok": True}
        except Exception as e:  # noqa: BLE001
            detail = ""
            if isinstance(e, httpx.HTTPStatusError) and e.response is not None:
                detail = f" | body={e.response.text[:300]}"
            return {"content": f"调用失败: {e}{detail}", "cost": self.m["cost"], "mock": False, "ok": False}


class AgnesAdapter(Adapter):
    """Agnes：chat / image 同步真实调用 + video 异步提交/轮询/下载。

    真实端点与 key 来自 config（apihub.agnes-ai.com/v1，OpenAI 兼容格式）。
    """

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.m['api_key']}", "Content-Type": "application/json"}

    async def _request(self, method: str, path: str, payload: dict | None = None, timeout: int = 60, retries: int = 2):
        """带重试的请求：免费 API 偶发 404/429/5xx/网络抖动，重试可大幅提升成功率。"""
        url = f"{self.m['endpoint'].rstrip('/')}{path}"
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    if method == "POST":
                        r = await client.post(url, json=payload, headers=self._headers())
                    else:
                        r = await client.get(url, headers=self._headers())
                if r.status_code in (404, 429) or r.status_code >= 500:
                    last_exc = httpx.HTTPStatusError(f"HTTP {r.status_code}", request=r.request, response=r)
                    if attempt < retries:
                        await asyncio.sleep(2)
                        continue
                    r.raise_for_status()
                else:
                    r.raise_for_status()
                return r.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_exc = e
                if attempt < retries:
                    await asyncio.sleep(2)
                    continue
                raise
        assert last_exc is not None
        raise last_exc

    async def _post(self, path: str, payload: dict, timeout: int = 60) -> dict:
        return await self._request("POST", path, payload, timeout)

    def _download_image(self, url: str) -> str | None:
        try:
            d = state.DOWNLOAD_DIR
            if not d:
                return None
            fname = f"agnes_{uuid.uuid4().hex[:8]}.png"
            with httpx.Client(timeout=120) as c:
                r = c.get(url)
                r.raise_for_status()
                (d / fname).write_bytes(r.content)
            return str(d / fname)
        except Exception:  # noqa: BLE001
            return None

    async def call(self, task_type: str, prompt: str, **kw) -> dict:
        if task_type == "chat":
            try:
                data = await self._post(
                    "/chat/completions",
                    {"model": "agnes-2.0-flash", "messages": [{"role": "user", "content": prompt}]},
                )
                content = data["choices"][0]["message"]["content"]
                return {"content": content, "cost": self.m["cost"], "mock": False, "ok": True}
            except Exception as e:  # noqa: BLE001
                return {"content": f"调用失败: {e}", "cost": self.m["cost"], "mock": False, "ok": False}
        if task_type == "image":
            try:
                data = await self._post(
                    "/images/generations",
                    {"model": "agnes-image-2.1-flash", "prompt": prompt, "size": "1024x768"},
                )
                url = data["data"][0]["url"]
                local = self._download_image(url)
                return {"content": local or url, "cost": self.m["cost"], "mock": False, "ok": True}
            except Exception as e:  # noqa: BLE001
                return {"content": f"调用失败: {e}", "cost": self.m["cost"], "mock": False, "ok": False}
        return {"content": "", "cost": self.m["cost"], "mock": False, "ok": False}

    # ---- 视频异步（供 routes_v1 后台任务调用，实时回写状态）----

    async def video_submit(self, prompt: str, duration: int) -> str:
        target = max(1, int(duration * 24))
        n = max(1, round((target - 1) / 8))
        num_frames = min(401, 8 * n + 1)
        payload = {
            "model": "agnes-video-v2.0",
            "prompt": prompt,
            "width": 768,
            "height": 1152,
            "num_frames": num_frames,
            "frame_rate": 24,
        }
        data = await self._post("/videos", payload, timeout=120)
        tid = data.get("task_id") or data.get("id")
        if not tid:
            raise RuntimeError(f"Agnes 未返回任务ID: {data}")
        return tid

    async def video_poll(self, agnes_tid: str) -> tuple[str | None, str]:
        st = await self._request("GET", f"/videos/{agnes_tid}", timeout=30)
        status = st.get("status")
        url = st.get("url") or st.get("video_url") or st.get("remixed_from_video_id") or ""
        return status, url

    async def video_download(self, url: str, download_dir, agnes_tid: str) -> str:
        fname = f"agnes_{agnes_tid}.mp4"
        path = download_dir / fname
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.get(url)
            r.raise_for_status()
            path.write_bytes(r.content)
        return str(path)


def get_adapter(model: dict) -> Adapter:
    if model["mode"] != "real" or not model["api_key"]:
        return MockAdapter(model)
    if model["id"] == "agnes":
        return AgnesAdapter(model)
    return OpenAICompatibleAdapter(model)
