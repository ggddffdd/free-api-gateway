"""路由策略引擎：按 task_type + 额度 + 策略选最优模型。"""
from __future__ import annotations
from . import state


def select_model(task_type: str, strategy: str | None = None) -> dict | None:
    strat = strategy or state.STRATEGY
    candidates = [
        m for m in state.MODELS.values()
        if m["enabled"] and task_type in m["supports"] and m["used"] < m["daily_limit"]
    ]
    if not candidates:
        # 退而求其次：允许超额模型（仅 mock 演示时能跑通），优先 mock
        candidates = [
            m for m in state.MODELS.values()
            if m["enabled"] and task_type in m["supports"]
        ]
        if not candidates:
            return None

    # 分值越高越优先；real 仅作次要 tiebreak
    if strat == "quality":
        key = lambda m: (m["mode"] == "real", m["quality"], -m["cost"])
    elif strat == "speed":
        key = lambda m: (m["mode"] == "real", m["speed"], -m["cost"])
    else:  # cost：优先最低 cost，其次质量最高
        key = lambda m: (m["mode"] == "real", -m["cost"], m["quality"])

    return sorted(candidates, key=key, reverse=True)[0]
