from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LlmCallResult:
    text: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    usd: float
