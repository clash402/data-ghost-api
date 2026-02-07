from __future__ import annotations

import json

from backend.src.core.settings import get_settings
from backend.src.llm.providers import LlmPrompt, persist_ledger, provider_from_env
from backend.src.llm.types import LlmCallResult


class ModelRouter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.provider = provider_from_env()

    def call(
        self,
        *,
        request_id: str,
        app: str,
        task: str,
        system_prompt: str,
        user_prompt: str,
        prefer_expensive: bool = False,
    ) -> LlmCallResult:
        model = self.settings.llm_expensive_model if prefer_expensive else self.settings.llm_cheap_model
        if task == "synthesize_explanation":
            model = self.settings.llm_expensive_model
        elif task == "default":
            model = self.settings.llm_default_model

        result = self.provider.call(model=model, prompt=LlmPrompt(system=system_prompt, user=user_prompt))
        persist_ledger(
            request_id=request_id,
            app=app,
            result=result,
            metadata={"task": task, "system_prompt_preview": system_prompt[:160], "user_prompt_preview": user_prompt[:160]},
        )
        return result


def try_parse_json(text: str) -> dict:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return {"raw": text}
    return {"raw": text}
