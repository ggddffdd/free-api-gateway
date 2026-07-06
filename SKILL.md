---
name: free-api-gateway
description: 统一网关调度5家免费大模型API（智谱/混元/硅基流动/魔搭/Agnes），支持chat/image/video三模态，按cost/quality/speed策略自动路由，含额度看板与Mock演示模式
dependency:
  python:
    - fastapi>=0.100.0
    - uvicorn>=0.23.0
    - httpx>=0.25.0
    - pyyaml>=6.0
---

# Free API Gateway — 免费大模型统一路由网关

## 任务目标

- 本 Skill 用于：将智谱、混元 Hy3、硅基流动、魔搭、Agnes 五家免费大模型平台编排为**单一 OpenAI 兼容入口**，智能体无需关心底层平台差异
- 能力包含：统一 chat/image/video 三模态调用、三策略自动路由（cost/quality/speed）、额度管理与实时看板、异步视频任务轮询下载
- 触发条件：用户需要免费调用大模型/生图/生视频，或希望多平台自动选最优可用通道

## 前置准备

- 依赖说明：见 dependency 区，执行 `pip install -r requirements.txt`
- 配置文件：复制 `config.example.yaml` 为 `config.yaml`，填入各平台 api_key；不填则自动进入 Mock 模式可演示全链路

## 操作步骤

### 标准流程：启动网关

1. 步骤一：安装依赖
   - 执行 `pip install -r requirements.txt`

2. 步骤二：启动服务
   - 执行 `uvicorn app.main:app --host 0.0.0.0 --port 8000`
   - 或使用一键脚本：`chmod +x start.sh && ./start.sh`
   - 或 Docker：`docker compose up --build`

3. 步骤三：验证运行
   - 打开浏览器访问 http://127.0.0.1:8000 查看额度看板

### 调用示例

**聊天（默认 cost 策略）：**
```
POST /v1/chat
Body: {"prompt": "用一句话介绍你自己"}
```

**生图（自动选支持 image 的模型）：**
```
POST /v1/image
Body: {"prompt": "赛博朋克风格的城市夜景"}
```

**生视频（异步任务）：**
```
POST /v1/video
Body: {"prompt": "海浪拍打礁石", "duration": 5}
返回 task_id，通过 GET /v1/video/{task_id} 轮询进度和结果
```

**指定策略/指定模型：**
```
POST /v1/chat
Body: {"prompt": "写个快排", "strategy": "quality", "model": "hunyuan"}
```

## 路由策略说明

| 策略 | 行为 | 适用场景 |
|------|------|----------|
| cost | 优先选单次额度消耗最低的可用模型（默认） | 省钱、批量处理 |
| quality | 优先选质量分最高的模型 | 复杂推理、代码生成 |
| speed | 优先选速度分最高的模型 | 实时对话、快速响应 |

## 已接入平台一览

| 平台 | 支持类型 | 单次成本(额度) | 备注 |
|------|----------|---------------|------|
| 智谱 GLM-4-Flash | chat | 1 | 免费，需注册 |
| 混元 Hy3 (TokenHub) | chat | 2 | 免费，需腾讯云 |
| 硅基流动 | chat, image | chat=2, image=10 | 免费，需注册 |
| 魔搭 Qwen3.5-27B | chat | 1 | 免费，需绑定阿里云 |
| Agnes AI | chat, image, video | chat=1, image=5, video=20 | 免费，自研 |

## 注意事项

- config.yaml 含真实密钥，已被 .gitignore 屏蔽不会入库
- Mock 模式下所有接口正常响应，适合演示与投稿录屏
- 视频生成为异步任务：提交后后台线程轮询状态并自动下载到 downloads/
- 各适配器内置重试机制（默认 2 次），偶发超时不影响使用
- Docker 部署时需在 docker-compose.yml 中挂载 config.yaml

## 使用示例

**场景一：智能体统一聊天入口**
> 用户说"帮我分析这段文本"，智能体直接 POST /v1/chat，网关自动选最省钱且有额度的模型。

**场景二：多模态内容创作流水线**
> 先 POST /v1/image 生成封面图 → 再 POST /v1/chat 生成文案 → 最后 POST /v1/video 生成宣传视频。

**场景三：预算受限的批量处理**
> 设置 strategy="cost"，网关优先消耗低成本的智谱/魔搭额度完成大量简单查询。
