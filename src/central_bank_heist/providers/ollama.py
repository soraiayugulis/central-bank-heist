"""Ollama (local) provider via HTTP API."""

from __future__ import annotations

import json
import re
import threading
from typing import Iterator

from central_bank_heist.config import ProviderConfig

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


class OllamaProvider:
    def __init__(self, config: ProviderConfig) -> None:
        try:
            import httpx
        except ImportError:
            raise ImportError("Install the 'ai' extra: pip install central-bank-heist[ai]")
        self._base = (config.base_url or "http://localhost:11434").rstrip("/")
        self._model = config.model or "llama3.1:8b"
        self._httpx = httpx

    def _payload(self, system: str, user: str, stream: bool) -> dict:
        return {
            "model": self._model,
            "stream": stream,
            "think": False,
            "keep_alive": "30m",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {
                "num_predict": 250,
                "temperature": 0.8,
            },
        }

    def complete(self, system: str, user: str) -> str:
        resp = self._httpx.post(
            f"{self._base}/api/chat",
            json=self._payload(system, user, stream=False),
            timeout=60.0,
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        return _THINK_RE.sub("", content).strip()

    def stream(self, system: str, user: str) -> Iterator[str]:
        with self._httpx.stream(
            "POST",
            f"{self._base}/api/chat",
            json=self._payload(system, user, stream=True),
            timeout=60.0,
        ) as resp:
            resp.raise_for_status()
            in_think = False
            for line in resp.iter_lines():
                if not line.strip():
                    continue
                data = json.loads(line)
                content = data.get("message", {}).get("content", "")
                if not content:
                    continue
                # Defensive: skip any residual <think> block tokens
                if "<think>" in content:
                    in_think = True
                    content = content.split("<think>", 1)[0]
                if "</think>" in content:
                    in_think = False
                    content = content.split("</think>", 1)[1]
                if content and not in_think:
                    yield content

    def warmup(self) -> None:
        """Preload the model in a background thread (fire-and-forget)."""

        def _ping() -> None:
            try:
                self._httpx.post(
                    f"{self._base}/api/generate",
                    json={
                        "model": self._model,
                        "prompt": "ready",
                        "stream": False,
                        "think": False,
                        "keep_alive": "30m",
                        "options": {"num_predict": 1},
                    },
                    timeout=120.0,
                )
            except Exception:
                pass

        threading.Thread(target=_ping, daemon=True, name="ollama-warmup").start()
