"""Anthropic Claude provider."""

from __future__ import annotations

from typing import Iterator

from central_bank_heist.config import ProviderConfig


class AnthropicProvider:
    def __init__(self, config: ProviderConfig) -> None:
        try:
            import anthropic
        except ImportError:
            raise ImportError("Install the 'ai' extra: pip install central-bank-heist[ai]")
        self._client = anthropic.Anthropic(api_key=config.api_key or None)
        self._model = config.model or "claude-sonnet-4-20250514"

    def complete(self, system: str, user: str) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=300,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text

    def stream(self, system: str, user: str) -> Iterator[str]:
        with self._client.messages.stream(
            model=self._model,
            max_tokens=300,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as s:
            for text in s.text_stream:
                yield text
