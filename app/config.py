"""配置加载：config.yaml 优先，不存在则回退到 config.example.yaml / 环境变量。"""
from __future__ import annotations
import os
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent

CONFIG_PATH = os.environ.get("GATEWAY_CONFIG", BASE_DIR / "config.yaml")
EXAMPLE_PATH = BASE_DIR / "config.example.yaml"


def load_config() -> dict:
    path = Path(CONFIG_PATH)
    if not path.exists():
        path = EXAMPLE_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    # 允许环境变量覆盖 api_key（生产建议走环境变量，不落盘）
    for mid, m in (raw.get("models") or {}).items():
        env_key = os.environ.get(f"APIKEY_{mid.upper()}")
        if env_key:
            m["api_key"] = env_key
    return raw
