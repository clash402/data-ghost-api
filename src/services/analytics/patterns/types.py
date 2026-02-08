from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PatternPlan:
    name: str
    queries: list[dict[str, str]] = field(default_factory=list)
    diagnostics: list[dict[str, str]] = field(default_factory=list)
