from __future__ import annotations

from typing import Any


def pick_metric_column(schema: dict[str, str], preferred: str | None = None) -> str | None:
    numeric = [name for name, kind in schema.items() if kind in {"INTEGER", "REAL"}]
    if preferred and preferred in numeric:
        return preferred
    return numeric[0] if numeric else None


def pick_time_column(columns: list[str], preferred: str | None = None) -> str | None:
    if preferred and preferred in columns:
        return preferred
    candidates = [
        c
        for c in columns
        if any(token in c.lower() for token in ["date", "time", "day", "week", "month", "year"])
    ]
    return candidates[0] if candidates else None


def pick_dimension_columns(schema: dict[str, str], exclude: set[str] | None = None) -> list[str]:
    exclude = exclude or set()
    dims = [name for name, kind in schema.items() if kind == "TEXT" and name not in exclude]
    return dims


def infer_top_n(intent: dict[str, Any], default: int = 5) -> int:
    try:
        return int(intent.get("top_n", default))
    except Exception:
        return default
