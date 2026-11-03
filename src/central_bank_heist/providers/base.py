"""LLM provider protocol and factory."""

from __future__ import annotations

from typing import Iterator, Protocol

from central_bank_heist.config import ProviderConfig


class LLMProvider(Protocol):
    """Minimal interface every provider must implement."""

    def complete(self, system: str, user: str) -> str:
        """Return a full completion string."""
        ...

    def stream(self, system: str, user: str) -> Iterator[str]:
        """Yield tokens as they arrive."""
        ...


def create_provider(config: ProviderConfig) -> LLMProvider:
    """Factory: create the right provider from config."""
    name = config.provider.lower()

    if name == "anthropic":
        from central_bank_heist.providers.anthropic import AnthropicProvider
        return AnthropicProvider(config)
    if name == "openai":
        from central_bank_heist.providers.openai import OpenAIProvider
        return OpenAIProvider(config)
    if name == "ollama":
        from central_bank_heist.providers.ollama import OllamaProvider
        return OllamaProvider(config)

    from central_bank_heist.providers.scripted import ScriptedProvider
    return ScriptedProvider()
