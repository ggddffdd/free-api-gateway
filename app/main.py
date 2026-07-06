"""入口模块：uvicorn app.main:app"""
from . import app  # noqa: F401  (app 定义见 __init__.py)

__all__ = ["app"]
