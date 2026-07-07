# 免费 API 统一网关 · Free API Gateway

> **一个入口，调度五家免费大模型。** 用腾讯混元 Hy3 在 WorkBuddy 中构建的统一路由服务：把智谱 / 混元 Hy3 / 硅基流动 / 魔搭 / Agnes 编排成单一 OpenAI 兼容入口，按任务类型 + 剩余额度 + 策略自动选最优模型，并自带实时额度看板。
>
> 🏆 参赛作品 · 腾讯混元 Hy3 超能力挑战赛（Coding + Agent 方向）

---

## ✨ 一句话简介

把五个免费平台收成一个网关——你只说"要聊 / 要生图 / 要生视频"，网关自己挑最划算的模型、管额度、出日志。

```text
  你 ──▶  /v1/chat | /v1/image | /v1/video  ──▶  网关(路由引擎)
                                                     │ 识别任务类型
                                                     │ 过滤可用模型
                                                     │ 结合额度+策略选优
                                                     ▼
                          智谱 ◀──▶ 混元Hy3 ◀──▶ 硅基流动 ◀──▶ 魔搭 ◀──▶ Agnes
```

---

## 🎯 为什么是 Hy3 写的

整个项目（FastAPI 后端、5 个平台适配器、路由策略引擎、ECharts 看板）由混元 Hy3 在 WorkBuddy 内一次性生成并自洽跑通，体现了双重能力：

- **Coding**：多平台 HTTP 适配器、路由打分算法、前后端一体交付；
- **Agent**：网关本身就是"多步决策 Agent"——识别任务 → 过滤可用模型 → 结合额度与策略选优 → 调用 → 记账 → 出日志。

---

## 🚀 功能一览

| 模块 | 说明 |
|------|------|
| 统一入口 | `POST /v1/chat`、`/v1/image`、`/v1/video` 三模态归一 |
| 多平台适配器 | 智谱 / 混元 Hy3 / 硅基流动 / 魔搭 / Agnes，各声明支持类型与单次成本 |
| 路由引擎 | 按 `task_type` + 额度 + 策略（cost / quality / speed）选最优模型 |
| 额度管家 | 配置每日上限，运行时统计已用，超额自动跳过 |
| 实时看板 | 各模型状态 / 额度进度 / 路由日志，前端每 3 秒自动刷新 |
| 视频异步 | Agnes 生视频为异步任务：提交 → 轮询状态 → 下载到本地 `downloads/` |
| Mock 模式 | 未填 key 也能跑通全链路，便于演示与投稿录屏 |

---

## ⚡ 快速开始

### 方式一：本地启动（推荐先试 Mock）

```bash
# 1. 安装依赖
pip3 install -r requirements.txt

# 2.（可选）填 key：复制样例并填入真实 api_key
cp config.example.yaml config.yaml
#   编辑 config.yaml，把对应模型的 api_key 填上

# 3. 启动（不填 key 即为 Mock 模式，可演示全链路）
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

打开 http://127.0.0.1:8000 即可看到额度看板。

### 方式二：Docker 一键启动

```bash
docker compose up --build
```

默认 Mock 模式（无需 key）。填了真实 key 后：先 `cp config.example.yaml config.yaml` 填 key，再打开 `docker-compose.yml` 里 volumes 注释挂载，然后 `docker compose up --build`。

### 方式三：本地一键脚本

```bash
chmod +x start.sh && ./start.sh
```

脚本自动装依赖并以 Mock 模式启动；填 key 方式同上。

---

## 📡 调用示例

```bash
# 聊天（默认 cost 策略 -> 选最省额度的模型）
curl -X POST http://127.0.0.1:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"用一句话介绍你自己"}'

# 生图（自动选支持 image 的模型）
curl -X POST http://127.0.0.1:8000/v1/image \
  -H "Content-Type: application/json" \
  -d '{"prompt":"赛博朋克风格的城市夜景"}'

# 生视频（异步：立即返回 task_id，后台线程轮询+下载）
curl -X POST http://127.0.0.1:8000/v1/video \
  -H "Content-Type: application/json" \
  -d '{"prompt":"海浪拍打礁石","duration":5}'
# 拿到 task_id 后查询进度/结果（看板也会实时显示）
curl http://127.0.0.1:8000/v1/video/<task_id>

# 指定策略 / 指定模型
curl -X POST http://127.0.0.1:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"写个快排","strategy":"quality","model":"hunyuan"}'
```

---

## 🧭 路由策略说明

| 策略 | 行为 | 适用场景 |
|------|------|---------|
| `cost` | 优先选单次额度消耗最低的可用模型（默认） | 省钱、批量处理 |
| `quality` | 优先选质量分最高的模型 | 复杂推理、代码生成 |
| `speed` | 优先选速度分最高的模型 | 实时对话、快速响应 |

---

## 🔌 已接入平台

| 平台 | 支持类型 | 单次成本(额度) | 备注 |
|------|----------|---------------|------|
| 智谱 GLM-4-Flash | chat | 1 | 免费，需注册 |
| 混元 Hy3 (TokenHub) | chat | 2 | 免费，需腾讯云 |
| 硅基流动 | chat, image | chat=2, image=10 | 免费，需注册 |
| 魔搭 Qwen3.5-27B | chat | 1 | 免费，需绑定阿里云 |
| Agnes AI | chat, image, video | chat=1, image=5, video=20 | 免费，自研 |

---

## 📁 项目结构

```text
free-api-gateway/
├── app/
│   ├── main.py          # 入口：uvicorn app.main:app
│   ├── config.py        # 配置加载
│   ├── state.py         # 额度/日志/任务状态管理
│   ├── router.py        # 路由策略引擎
│   ├── adapters.py      # 5 家平台适配器
│   ├── routes_v1.py     # /v1/chat|image|video 接口
│   ├── routes_meta.py   # /api/status|logs|tasks 看板数据
│   └── static/
│       └── index.html   # 实时额度看板
├── config.example.yaml  # 配置样例（不含密钥）
├── requirements.txt
├── Dockerfile / docker-compose.yml
├── start.sh
└── SKILL.md             # 魔搭/小红书 Skill 定义
```

---

## 📝 投稿信息

- 参赛赛事：腾讯混元 Hy3 超能力挑战赛（Coding + Agent）
- 核心交付：`app/` 全套源码（适配 5 平台 + 路由引擎 + 看板）
- 演示素材：本地 Mock 跑通录屏（无需 key）、填 key 后真实调用截图（chat / image / video 各一张）
- 截止时间：**2026-07-22 23:59**

> ⚠️ 投稿前请脱敏任何私有 key；`config.yaml` 已被 `.gitignore` 屏蔽，不会进入仓库。

---

## ⚠️ 注意事项

- `config.yaml` 含真实密钥，已被 `.gitignore` 屏蔽，不会入库；
- Mock 模式下所有接口正常响应，适合演示与投稿录屏；
- 视频生成为异步任务：提交后后台线程轮询状态并自动下载到 `downloads/`；
- 各适配器内置重试机制（默认 2 次），偶发超时不影响使用；
- Docker 部署时需在 `docker-compose.yml` 中挂载 `config.yaml`。
