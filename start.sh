#!/usr/bin/env bash
# 本地一键启动（Mock 模式，无需任何 key）
set -euo pipefail
cd "$(dirname "$0")"

echo "==> 创建虚拟环境并安装依赖"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt

echo "==> 以 Mock 模式启动网关 (http://127.0.0.1:8000)"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
