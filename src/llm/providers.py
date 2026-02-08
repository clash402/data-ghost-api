from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from src.core.settings import get_settings
from src.llm.types import LlmCallResult
from src.storage.repositories import insert_cost_ledger
from src.utils.time import utc_now_iso


@dataclass
class LlmPrompt:
    system: str
    user: str


class BaseProvider:
    provider_name = "base"

    def __init__(self) -> None:
        self.settings = get_settings()

    def _estimate_price(self, prompt_tokens: int, completion_tokens: int) -> float:
        prompt = (prompt_tokens / 1000) * self.settings.llm_price_prompt_per_1k
        completion = (completion_tokens / 1000) * self.settings.llm_price_completion_per_1k
        return round(prompt + completion, 8)

    def call(self, model: str, prompt: LlmPrompt) -> LlmCallResult:
        raise NotImplementedError


class MockProvider(BaseProvider):
    provider_name = "mock"

    def call(self, model: str, prompt: LlmPrompt) -> LlmCallResult:
        user_text = prompt.user.strip()
        response = {
            "summary": user_text[:300],
            "note": "mock-provider-response",
        }
        prompt_tokens = len((prompt.system + "\n" + prompt.user).split())
        completion_tokens = len(json.dumps(response).split())
        usd = self._estimate_price(prompt_tokens, completion_tokens)
        return LlmCallResult(
            text=json.dumps(response),
            model=model,
            provider=self.provider_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            usd=usd,
        )


class OpenAIProvider(BaseProvider):
    provider_name = "openai"

    def __init__(self) -> None:
        super().__init__()
        try:
            from langchain_openai import ChatOpenAI
        except Exception as exc:
            raise RuntimeError("OpenAI provider requires langchain-openai") from exc
        self._chat_class = ChatOpenAI

    def call(self, model: str, prompt: LlmPrompt) -> LlmCallResult:
        from langchain_core.messages import HumanMessage, SystemMessage

        chat = self._chat_class(model=model, api_key=self.settings.llm_openai_api_key, temperature=0)
        output = chat.invoke([SystemMessage(content=prompt.system), HumanMessage(content=prompt.user)])
        text = str(output.content)
        prompt_tokens = len((prompt.system + "\n" + prompt.user).split())
        completion_tokens = len(text.split())
        usd = self._estimate_price(prompt_tokens, completion_tokens)
        return LlmCallResult(
            text=text,
            model=model,
            provider=self.provider_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            usd=usd,
        )


class AnthropicProvider(BaseProvider):
    provider_name = "anthropic"

    def __init__(self) -> None:
        super().__init__()
        try:
            from langchain_anthropic import ChatAnthropic
        except Exception as exc:
            raise RuntimeError("Anthropic provider requires langchain-anthropic") from exc
        self._chat_class = ChatAnthropic

    def call(self, model: str, prompt: LlmPrompt) -> LlmCallResult:
        from langchain_core.messages import HumanMessage, SystemMessage

        chat = self._chat_class(model=model, api_key=self.settings.llm_anthropic_api_key, temperature=0)
        output = chat.invoke([SystemMessage(content=prompt.system), HumanMessage(content=prompt.user)])
        text = str(output.content)
        prompt_tokens = len((prompt.system + "\n" + prompt.user).split())
        completion_tokens = len(text.split())
        usd = self._estimate_price(prompt_tokens, completion_tokens)
        return LlmCallResult(
            text=text,
            model=model,
            provider=self.provider_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            usd=usd,
        )


def provider_from_env() -> BaseProvider:
    provider = get_settings().llm_provider.lower()
    if provider == "openai":
        return OpenAIProvider()
    if provider == "anthropic":
        return AnthropicProvider()
    return MockProvider()


def persist_ledger(
    *,
    request_id: str | None,
    app: str,
    result: LlmCallResult,
    metadata: dict,
) -> None:
    insert_cost_ledger(
        ledger_id=str(uuid.uuid4()),
        request_id=request_id,
        app=app,
        provider=result.provider,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        usd=result.usd,
        created_at=utc_now_iso(),
        metadata=metadata,
    )
