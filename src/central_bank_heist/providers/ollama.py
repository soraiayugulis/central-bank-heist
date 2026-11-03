"""Ollama (local) provider via HTTP API."""

from __future__ import annotations

import json
from typing import Iterator

from central_bank_heist.config import ProviderConfig


class OllamaProvider:
    def __init__(self, config: ProviderConfig) -> None:
        try:
            import httpx
        except ImportError:
            raise ImportError("Install the 'ai' extra: pip install central-bank-heist[ai]")
        self._base = (config.base_url or "http://localhost:11434").rstrip("/")
        self._model = config.model or "llama3.1:8b"
        self._httpx = httpx

    def complete(self, system: str, user: str) -> str:
        resp = self._httpx.post(
            f"{self._base}/api/chat",
            json={
                "model": self._model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def stream(self, system: str, user: str) -> Iterator[str]:
        with self._httpx.stream(
            "POST",
            f"{self._base}/api/chat",
            json={
                "model": self._model,
                "stream": True,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=60.0,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line.strip():
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
