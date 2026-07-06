# 免费 API 统一网关（Free API Gateway）

> 用 **腾讯混元 Hy3** 在 WorkBuddy 写的一个统一路由服务：把多个免费大模型/多模态平台编排成**一个入口**，按任务类型 + 剩余额度 + 策略自动选最优模型，并带额度看板。
> 参赛作品 · 腾讯混元 Hy3 超能力挑战赛（Coding + Agent 方向）。

---

## 一句话简介

把智谱 / 混元 Hy3 / 硅基流动 / 魔搭 / Agnes 五个免费平台，用一个网关统一调度——你只说"要聊/要生图/要生视频"，网关自己挑最划算的模型并管额度。

## 为什么是 Hy3 写的

整个项目（FastAPI 后端、5 个平台适配器、路由策略引擎、ECharts 看板）由 Hy3 在 WorkBuddy 内一次性生成并自洽跑通，体现了：

- **Coding**：多平台 HTTP 适配器、路由打分算法、前后端一体；
- **Agent**：网关本身就是"多步决策 Agent"——识别任务 → 过滤可用模型 → 结合额度与策略选优 → 调用 → 记账 → 出日志。

## 功能

| 模块 | 说明 |
|------|------|
| 统一入口 | `POST /v1/chat`、`/v1/image`、`/v1/video` |
| 适配器 | 智谱 / 混元 Hy3 / 硅基流动 / 魔搭 / Agnes，各声明支持类型与单次成本 |
| 路由引擎 | 按 `task_type` + 额度 + 策略（cost / quality / speed）选最优 |
| 额度管家 | 配置每日上限、运行时统计已用、超额自动跳过 |
| 看板 | 各模型状态 / 额度进度 / 路由日志（自动刷新） |
| 视频异步 | Agnes 生视频为异步任务：提交 → 轮询状态 → 下载到本地 `downloads/` |
| Mock 模式 | 未填 key 也能跑通全链路，便于演示与投稿录屏 |

## 快速开始

```bash
# 1. 安装依赖
pip3 install -r requirements.txt

# 2. （可选）填 key：复制样例并填入真实 api_key
cp config.example.yaml config.yaml
#   编辑 config.yaml，把对应模型的 api_key 填上

# 3. 启动（Mock 模式即可演示，无需任何 key）
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

打开 http://127.0.0.1:8000 看额度看板。

## Docker 一键启动

```bash
docker compose up --build
```

默认 Mock 模式（无需 key）。填了真实 key 后：先 `cp config.example.yaml config.yaml` 填 key，再打开 `docker-compose.yml` 里 volumes 注释挂载，然后 `docker compose up --build`。

## 本地一键脚本

```bash
chmod +x start.sh && ./start.sh
```

脚本自动装依赖并以 Mock 模式启动；填 key 方式同上。

## 调用示例

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

## 路由策略说明

- `cost`：优先选单次额度消耗最低的可用模型（默认，省钱）。
- `quality`：优先选质量分最高的模型（如 chat/code 会优先 Hy3）。
- `speed`：优先选速度分最高的模型。

## 投稿素材清单

1. `app/` 全套源码（适配 5 平台 + 路由引擎 + 看板）—— 核心交付物
2. 本地 Mock 跑通录屏（无需 key，直接演示路由与看板）
3. 填 key 后真实调用的截图（chat / image / video 各一张）
4. 一句话简介（见上）

> 截止 2026-07-22 23:59。投稿前脱敏任何私有 key。
