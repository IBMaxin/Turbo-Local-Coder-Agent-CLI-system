"""Backend Manager - Unified interface for Ollama and llama.cpp backends."""
from __future__ import annotations

import json
import logging
import atexit
from typing import Any, Iterator, Optional
from dataclasses import dataclass

import httpx

from .config import Settings


@dataclass
class ChatResponse:
    """Standardized response from any backend."""
    content: str
    tool_calls: list[dict] = None
    done: bool = False
    

class BaseBackend:
    """Base class for LLM backends with connection pooling."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Connection pool for better performance
        self._client = httpx.Client(
            timeout=httpx.Timeout(settings.request_timeout_s, connect=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            follow_redirects=True
        )
        
        # Register cleanup
        atexit.register(self._cleanup)
    
    def _cleanup(self):
        """Close HTTP client on exit."""
        if hasattr(self, '_client'):
            self._client.close()
    
    def chat(self, messages: list[dict], model: str, tools: list[dict] = None, 
             stream: bool = True) -> Iterator[ChatResponse]:
        """Send chat request and yield responses."""
        raise NotImplementedError
    
    def is_available(self) -> bool:
        """Check if backend is available."""
        raise NotImplementedError
    
    def get_models(self) -> list[str]:
        """List available models."""
        raise NotImplementedError


class OllamaBackend(BaseBackend):
    """Ollama backend with optimized parameters."""
    
    def chat(self, messages: list[dict], model: str, tools: list[dict] = None,
             stream: bool = True) -> Iterator[ChatResponse]:
        """Send chat to Ollama API with optimizations."""
        url = f"{self.settings.local_host}/api/chat"
        
        # Highly optimized parameters for speed
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "num_predict": 2048,      # Max tokens
                "temperature": 0.05,       # Very low = faster + deterministic
                "top_p": 0.85,             # Nucleus sampling
                "top_k": 20,               # Reduced for speed
                "repeat_penalty": 1.05,    # Light penalty
                "num_thread": 8,           # Max CPU threads
                "num_batch": 512,          # Batch size
                "num_ctx": 4096,           # Context window
                "stop": ["</tool_call>", "<|end|>", "<|endoftext|>"],
            }
        }
        
        # Only add tools if provided
        if tools:
            payload["tools"] = tools
        
        self.logger.debug(f"Ollama {model}: {len(messages)} messages, stream={stream}")
        
        try:
            if not stream:
                # Non-streaming: single response
                resp = self._client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                msg = data.get("message", {}) or {}
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls")
                
                # Log performance
                self._log_performance(data)
                
                yield ChatResponse(
                    content=content,
                    tool_calls=tool_calls,
                    done=True
                )
            else:
                # Streaming: yield chunks
                with self._client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    
                    chunks = []
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
        """Log performance metrics if available."""
        if "eval_count" in data and "eval_duration" in data:
            tokens = data["eval_count"]
            duration_ns = data["eval_duration"]
            if duration_ns > 0:
                tok_per_sec = tokens / (duration_ns / 1e9)
                self.logger.info(f"⚡ {tokens} tokens @ {tok_per_sec:.1f} tok/s")
    
    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            url = f"{self.settings.local_host}/api/tags"
            resp = self._client.get(url, timeout=3)
            return resp.status_code == 200
        except Exception as e:
            self.logger.debug(f"Ollama unavailable: {e}")
            return False
    
    def get_models(self) -> list[str]:
        """List Ollama models."""
        try:
            url = f"{self.settings.local_host}/api/tags"
            resp = self._client.get(url, timeout=5)
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
        """Ensure llama.cpp server is running."""
        from .llamacpp_server import LlamaCppServer
        
        self.server = LlamaCppServer(self.settings)
        if not self.server.is_running():
            self.logger.info("🚀 Starting llama.cpp server...")
            self.server.start()
    
    def chat(self, messages: list[dict], model: str, tools: list[dict] = None,
             stream: bool = True) -> Iterator[ChatResponse]:
        """Send chat to llama.cpp OpenAI API."""
        if not self.server or not self.server.is_running():
            self._ensure_server()
        
        url = f"http://127.0.0.1:{self.settings.llamacpp_port}/v1/chat/completions"
        
        # Optimized payload
        payload = {
            "messages": messages,
            "stream": stream,
            "max_tokens": 2048,
            "temperature": 0.05,  # Low = fast + deterministic
            "top_p": 0.85,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1,
        }
        
        if tools:
            payload["tools"] = tools
        
        self.logger.debug(f"llama.cpp: {len(messages)} messages, stream={stream}")
        
        try:
            if not stream:
                # Non-streaming
                resp = self._client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    yield ChatResponse(
                        content=message.get("content", ""),
                        tool_calls=message.get("tool_calls"),
                        done=True
                    )
            else:
                # Streaming
                with self._client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    
                    chunks = []
                    tool_calls = None
                    
                    for line in resp.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        
                        line = line[6:]  # Remove "data: "
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
                        chunk = delta.get("content", "")
                        
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
        """Check if llama.cpp server is running."""
        return self.server and self.server.is_running()
    
    def get_models(self) -> list[str]:
        """Get loaded model path."""
        if self.settings.llamacpp_model_path:
            return [self.settings.llamacpp_model_path]
        return []
    
    def shutdown(self):
        """Stop llama.cpp server."""
        if self.server:
            self.server.stop()
        self._cleanup()


def get_backend(settings: Settings) -> BaseBackend:
    """Factory function to get the appropriate backend."""
    backend_type = settings.backend.lower()
    
    if backend_type == "llamacpp":
        return LlamaCppBackend(settings)
    elif backend_type == "ollama":
        return OllamaBackend(settings)
    else:
        raise ValueError(
            f"Unknown backend: '{backend_type}'.\n"
            "Valid options: 'ollama' or 'llamacpp'"
        )
