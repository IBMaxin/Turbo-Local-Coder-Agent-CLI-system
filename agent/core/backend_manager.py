"""Backend Manager - Unified interface for Ollama, llama.cpp, and LM Studio backends."""
from __future__ import annotations

import json
import logging
import atexit
from typing import Any, Iterator, Optional
from dataclasses import dataclass, field

import httpx

from .config import Settings


@dataclass
class ChatResponse:
    """Standardized response from any backend."""
    content: str
    tool_calls: Optional[list[dict]] = field(default=None)
    done: bool = False


class BaseBackend:
    """Base class for LLM backends with connection pooling."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)

        self._client = httpx.Client(
            timeout=httpx.Timeout(settings.request_timeout_s, connect=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            follow_redirects=True
        )
        atexit.register(self._cleanup)

    def _cleanup(self):
        if hasattr(self, '_client'):
            self._client.close()

    def chat(self, messages: list[dict], model: str, tools: list[dict] = None,
             stream: bool = True) -> Iterator[ChatResponse]:
        raise NotImplementedError

    def is_available(self) -> bool:
        raise NotImplementedError

    def get_models(self) -> list[str]:
        raise NotImplementedError


class LMStudioBackend(BaseBackend):
    """LM Studio backend using its OpenAI-compatible local API (http://localhost:1234/v1)."""

    def chat(self, messages: list[dict], model: str, tools: list[dict] = None,
             stream: bool = True) -> Iterator[ChatResponse]:
        """Send chat to LM Studio OpenAI-compatible API."""
        url = f"{self.settings.lmstudio_host}/v1/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "max_tokens": 2048,
            "temperature": 0.05,
            "top_p": 0.85,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1,
        }

        if tools:
            payload["tools"] = tools

        self.logger.debug(f"LM Studio {model}: {len(messages)} messages, stream={stream}")

        try:
            if not stream:
                resp = self._client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    yield ChatResponse(
                        content=message.get("content", "") or "",
                        tool_calls=message.get("tool_calls"),
                        done=True
                    )
                else:
                    yield ChatResponse(content="", done=True)
            else:
                with self._client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()

                    chunks: list[str] = []
                    tool_calls = None

                    for line in resp.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue

                        data_str = line[6:]  # Remove "data: "
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        choices = data.get("choices", [])
                        if not choices:
                            continue

                        delta = choices[0].get("delta", {})
                        chunk = delta.get("content") or ""

                        if chunk:
                            chunks.append(chunk)
                            yield ChatResponse(content=chunk, done=False)

                        if delta.get("tool_calls"):
                            tool_calls = delta["tool_calls"]

                        if choices[0].get("finish_reason") == "stop":
                            yield ChatResponse(
                                content="".join(chunks),
                                tool_calls=tool_calls,
                                done=True
                            )
                            break

        except httpx.HTTPError as e:
            self.logger.error(f"LM Studio request failed: {e}")
            raise

    def is_available(self) -> bool:
        """Check if LM Studio server is running."""
        try:
            resp = self._client.get(f"{self.settings.lmstudio_host}/v1/models", timeout=3)
            return resp.status_code == 200
        except Exception as e:
            self.logger.debug(f"LM Studio unavailable: {e}")
            return False

    def get_models(self) -> list[str]:
        """List models loaded in LM Studio."""
        try:
            resp = self._client.get(f"{self.settings.lmstudio_host}/v1/models", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception as e:
            self.logger.error(f"Failed to list LM Studio models: {e}")
            return []


class OllamaBackend(BaseBackend):
    """Ollama backend with optimized parameters."""

    def chat(self, messages: list[dict], model: str, tools: list[dict] = None,
             stream: bool = True) -> Iterator[ChatResponse]:
        url = f"{self.settings.local_host}/api/chat"

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "num_predict": 2048,
                "temperature": 0.05,
                "top_p": 0.85,
                "top_k": 20,
                "repeat_penalty": 1.05,
                "num_thread": 8,
                "num_batch": 512,
                "num_ctx": 4096,
                "stop": ["</tool_call>", "<|end|>", "<|endoftext|>"],
            }
        }

        if tools:
            payload["tools"] = tools

        self.logger.debug(f"Ollama {model}: {len(messages)} messages, stream={stream}")

        try:
            if not stream:
                resp = self._client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

                msg = data.get("message", {}) or {}
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls")
                self._log_performance(data)

                yield ChatResponse(content=content, tool_calls=tool_calls, done=True)
            else:
                with self._client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()

                    chunks: list[str] = []
                    tool_calls = None

                    for line in resp.iter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        msg = data.get("message", {}) or {}
                        chunk = msg.get("content", "")

                        if chunk:
                            chunks.append(chunk)
                            yield ChatResponse(content=chunk, done=False)

                        if msg.get("tool_calls"):
                            tool_calls = msg["tool_calls"]

                        if data.get("done"):
                            self._log_performance(data)
                            yield ChatResponse(
                                content="".join(chunks),
                                tool_calls=tool_calls,
                                done=True
                            )
                            break
        except httpx.HTTPError as e:
            self.logger.error(f"Ollama request failed: {e}")
            raise

    def _log_performance(self, data: dict):
        if "eval_count" in data and "eval_duration" in data:
            tokens = data["eval_count"]
            duration_ns = data["eval_duration"]
            if duration_ns > 0:
                tok_per_sec = tokens / (duration_ns / 1e9)
                self.logger.info(f"⚡ {tokens} tokens @ {tok_per_sec:.1f} tok/s")

    def is_available(self) -> bool:
        try:
            resp = self._client.get(f"{self.settings.local_host}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception as e:
            self.logger.debug(f"Ollama unavailable: {e}")
            return False

    def get_models(self) -> list[str]:
        try:
            resp = self._client.get(f"{self.settings.local_host}/api/tags", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            self.logger.error(f"Failed to list models: {e}")
            return []


class LlamaCppBackend(BaseBackend):
    """llama.cpp backend with OpenAI-compatible API."""

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.server = None
        self._ensure_server()

    def _ensure_server(self):
        from .llamacpp_server import LlamaCppServer
        self.server = LlamaCppServer(self.settings)
        if not self.server.is_running():
            self.logger.info("🚀 Starting llama.cpp server...")
            self.server.start()

    def chat(self, messages: list[dict], model: str, tools: list[dict] = None,
             stream: bool = True) -> Iterator[ChatResponse]:
        if not self.server or not self.server.is_running():
            self._ensure_server()

        url = f"http://127.0.0.1:{self.settings.llamacpp_port}/v1/chat/completions"

        payload = {
            "messages": messages,
            "stream": stream,
            "max_tokens": 2048,
            "temperature": 0.05,
            "top_p": 0.85,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1,
        }

        if tools:
            payload["tools"] = tools

        try:
            if not stream:
                resp = self._client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    yield ChatResponse(
                        content=message.get("content", "") or "",
                        tool_calls=message.get("tool_calls"),
                        done=True
                    )
            else:
                with self._client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    chunks: list[str] = []
                    tool_calls = None

                    for line in resp.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        line = line[6:]
                        if line == "[DONE]":
                            break
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        choices = data.get("choices", [])
                        if not choices:
                            continue

                        delta = choices[0].get("delta", {})
                        chunk = delta.get("content") or ""

                        if chunk:
                            chunks.append(chunk)
                            yield ChatResponse(content=chunk, done=False)

                        if delta.get("tool_calls"):
                            tool_calls = delta["tool_calls"]

                        if choices[0].get("finish_reason") == "stop":
                            yield ChatResponse(
                                content="".join(chunks),
                                tool_calls=tool_calls,
                                done=True
                            )
                            break
        except httpx.HTTPError as e:
            self.logger.error(f"llama.cpp request failed: {e}")
            raise

    def is_available(self) -> bool:
        return self.server and self.server.is_running()

    def get_models(self) -> list[str]:
        if self.settings.llamacpp_model_path:
            return [self.settings.llamacpp_model_path]
        return []

    def shutdown(self):
        if self.server:
            self.server.stop()
        self._cleanup()


def get_backend(settings: Settings) -> BaseBackend:
    """Factory function to get the appropriate backend."""
    backend_type = settings.backend.lower()

    if backend_type == "lmstudio":
        return LMStudioBackend(settings)
    elif backend_type == "llamacpp":
        return LlamaCppBackend(settings)
    elif backend_type == "ollama":
        return OllamaBackend(settings)
    else:
        raise ValueError(
            f"Unknown backend: '{backend_type}'.\n"
            "Valid options: 'lmstudio', 'ollama', or 'llamacpp'"
        )
