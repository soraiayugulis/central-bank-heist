"""OpenAI provider."""

from __future__ import annotations

from typing import Iterator

from central_bank_heist.config import ProviderConfig


class OpenAIProvider:
    def __init__(self, config: ProviderConfig) -> None:
        try:
            import openai
        except ImportError:
            raise ImportError("Install the 'ai' extra: pip install central-bank-heist[ai]")
        kwargs: dict = {}
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.base_url:
            kwargs["base_url"] = config.base_url
        self._client = openai.OpenAI(**kwargs)
        self._model = config.model or "gpt-4o-mini"

    def complete(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=300,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""

    def stream(self, system: str, user: str) -> Iterator[str]:
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=300,
            stream=True,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        for chunk in resp:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
