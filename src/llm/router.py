from __future__ import annotations

from datetime import UTC, datetime
import json

from src.core.settings import get_settings
from src.llm.providers import LlmPrompt, persist_ledger, provider_from_env
from src.llm.types import LlmCallResult
from src.storage.repositories import get_global_spend_usd_since, get_request_spend_usd


class LlmDisabledError(Exception):
    pass


class LlmBudgetExceededError(Exception):
    pass


class ModelRouter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.provider = provider_from_env()

    def _estimate_price(self, prompt_tokens: int, completion_tokens: int) -> float:
        prompt = (prompt_tokens / 1000) * self.settings.llm_price_prompt_per_1k
        completion = (completion_tokens / 1000) * self.settings.llm_price_completion_per_1k
        return round(prompt + completion, 8)

    def _enforce_budget(self, *, request_id: str, estimated_usd: float) -> None:
        request_spend = get_request_spend_usd(request_id)
        projected_request_spend = request_spend + estimated_usd
        if projected_request_spend > self.settings.llm_max_usd_per_request:
            raise LlmBudgetExceededError(
                f"Per-request budget exceeded: projected ${projected_request_spend:.4f} > "
                f"${self.settings.llm_max_usd_per_request:.4f}"
            )

        today_start = (
            datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        )
        daily_spend = get_global_spend_usd_since(today_start)
        projected_daily_spend = daily_spend + estimated_usd
        if projected_daily_spend > self.settings.llm_max_usd_per_day:
            raise LlmBudgetExceededError(
                f"Daily budget exceeded: projected ${projected_daily_spend:.4f} > "
                f"${self.settings.llm_max_usd_per_day:.4f}"
            )

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
        model = (
            self.settings.llm_expensive_model if prefer_expensive else self.settings.llm_cheap_model
        )
        if task == "synthesize_explanation":
            model = self.settings.llm_expensive_model
        elif task == "default":
            model = self.settings.llm_default_model

        if not self.settings.llm_enabled:
            raise LlmDisabledError("LLM calls are disabled by configuration (LLM_ENABLED=false).")

        prompt_tokens = len((system_prompt + "\n" + user_prompt).split())
        estimated_completion_tokens = max(int(self.settings.llm_estimated_completion_tokens), 1)
        estimated_usd = self._estimate_price(prompt_tokens, estimated_completion_tokens)
        self._enforce_budget(request_id=request_id, estimated_usd=estimated_usd)

        result = self.provider.call(
            model=model, prompt=LlmPrompt(system=system_prompt, user=user_prompt)
        )
        persist_ledger(
            request_id=request_id,
            app=app,
            result=result,
            metadata={
                "task": task,
                "system_prompt_preview": system_prompt[:160],
                "user_prompt_preview": user_prompt[:160],
            },
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
