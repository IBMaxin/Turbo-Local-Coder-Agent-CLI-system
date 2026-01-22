"""Backend Manager - Unified interface for Ollama and llama.cpp backends."""
from __future__ import annotations

import json
import logging
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
    """Base class for LLM backends."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
    
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
    """Ollama backend implementation."""
    
    def chat(self, messages: list[dict], model: str, tools: list[dict] = None,
             stream: bool = True) -> Iterator[ChatResponse]:
        """Send chat to Ollama API."""
        url = f"{self.settings.local_host}/api/chat"
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        
        if tools:
            payload["tools"] = tools
        
        self.logger.debug(f"Ollama request to {url} with model {model}, stream={stream}")
        
        with httpx.Client(timeout=self.settings.request_timeout_s) as client:
            if not stream:
                # Non-streaming mode - get complete response
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                msg = data.get("message", {}) or {}
                content = msg.get("content") or ""
                tool_calls = msg.get("tool_calls") or []
                
                yield ChatResponse(
                    content=content,
                    tool_calls=tool_calls if tool_calls else None,
                    done=True
                )
            else:
                # Streaming mode
                with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    
                    content_chunks = []
                    tool_calls = []
                    
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        
                        msg = data.get("message", {}) or {}
                        chunk = msg.get("content") or ""
                        
                        if chunk:
                            content_chunks.append(chunk)
                            yield ChatResponse(content=chunk, done=False)
                        
                        calls = msg.get("tool_calls") or []
                        if calls:
                            tool_calls = calls
                        
                        if data.get("done", False):
                            final_content = "".join(content_chunks)
                            yield ChatResponse(
                                content=final_content,
                                tool_calls=tool_calls if tool_calls else None,
                                done=True
                            )
                            break
    
    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            url = f"{self.settings.local_host}/api/tags"
            with httpx.Client(timeout=5) as client:
                resp = client.get(url)
                return resp.status_code == 200
        except Exception as e:
            self.logger.warning(f"Ollama not available: {e}")
            return False
    
    def get_models(self) -> list[str]:
        """List Ollama models."""
        try:
            url = f"{self.settings.local_host}/api/tags"
            with httpx.Client(timeout=5) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            self.logger.error(f"Failed to get Ollama models: {e}")
            return []


class LlamaCppBackend(BaseBackend):
    """llama.cpp backend implementation."""
    
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.server = None
        self._ensure_server()
    
    def _ensure_server(self):
        """Ensure llama.cpp server is running."""
        from .llamacpp_server import LlamaCppServer
        
        self.server = LlamaCppServer(self.settings)
        if not self.server.is_running():
            self.logger.info("Starting llama.cpp server...")
            self.server.start()
    
    def chat(self, messages: list[dict], model: str, tools: list[dict] = None,
             stream: bool = True) -> Iterator[ChatResponse]:
        """Send chat to llama.cpp server."""
        if not self.server or not self.server.is_running():
            self._ensure_server()
        
        url = f"http://127.0.0.1:{self.settings.llamacpp_port}/v1/chat/completions"
        
        payload = {
            "messages": messages,
            "stream": stream,
        }
        
        if tools:
            payload["tools"] = tools
        
        self.logger.debug(f"llama.cpp request to {url}, stream={stream}")
        
        with httpx.Client(timeout=self.settings.request_timeout_s) as client:
            if not stream:
                # Non-streaming mode
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    content = message.get("content") or ""
                    tool_calls = message.get("tool_calls") or []
                    
                    yield ChatResponse(
                        content=content,
                        tool_calls=tool_calls if tool_calls else None,
                        done=True
                    )
            else:
                # Streaming mode
                with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    
                    content_chunks = []
                    tool_calls = []
                    
                    for line in resp.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        
                        line = line[6:]  # Remove "data: " prefix
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
                            content_chunks.append(chunk)
                            yield ChatResponse(content=chunk, done=False)
                        
                        # Check for tool calls
                        if "tool_calls" in delta:
                            tool_calls = delta["tool_calls"]
                        
                        if choices[0].get("finish_reason") == "stop":
                            final_content = "".join(content_chunks)
                            yield ChatResponse(
                                content=final_content,
                                tool_calls=tool_calls if tool_calls else None,
                                done=True
                            )
                            break
    
    def is_available(self) -> bool:
        """Check if llama.cpp server is running."""
        return self.server and self.server.is_running()
    
    def get_models(self) -> list[str]:
        """List loaded model."""
        if self.settings.llamacpp_model_path:
            return [self.settings.llamacpp_model_path]
        return []
    
    def shutdown(self):
        """Stop llama.cpp server."""
        if self.server:
            self.logger.info("Stopping llama.cpp server...")
            self.server.stop()


def get_backend(settings: Settings) -> BaseBackend:
    """Get the appropriate backend based on settings."""
    backend_type = settings.backend.lower()
    
    if backend_type == "llamacpp":
        return LlamaCppBackend(settings)
    elif backend_type == "ollama":
        return OllamaBackend(settings)
    else:
        raise ValueError(f"Unknown backend: {backend_type}. Use 'ollama' or 'llamacpp'")
