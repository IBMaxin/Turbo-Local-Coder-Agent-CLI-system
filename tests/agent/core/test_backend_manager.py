"""
Tests for agent/core/backend_manager.py
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch, MagicMock, mock_open
from typing import Iterator

from agent.core.backend_manager import (
    BaseBackend, OllamaBackend, LlamaCppBackend, get_backend, ChatResponse
)
from agent.core.config import Settings


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(
        turbo_host="http://localhost:8000",
        local_host="http://localhost:11434",
        planner_model="test-planner",
        coder_model="test-coder",
        api_key="test-api-key-12345",
        max_steps=25,
        request_timeout_s=120,
        dry_run=False,
        backend="ollama",
        llamacpp_model_path="./test-model.gguf",
        llamacpp_port=8080
    )


class TestBaseBackend:
    """Tests for BaseBackend class."""

    def test_init_creates_client(self, mock_settings: Settings):
        """Test BaseBackend initialization creates HTTP client."""
        with patch('httpx.Client') as mock_client:
            backend = BaseBackend(mock_settings)
            mock_client.assert_called_once()
            assert backend.settings == mock_settings

    def test_cleanup_closes_client(self, mock_settings: Settings):
        """Test cleanup closes HTTP client."""
        mock_client = MagicMock()
        with patch('httpx.Client', return_value=mock_client):
            backend = BaseBackend(mock_settings)
            backend._cleanup()
            mock_client.close.assert_called_once()


class TestOllamaBackend:
    """Tests for OllamaBackend class."""

    @pytest.fixture
    def ollama_backend(self, mock_settings: Settings) -> OllamaBackend:
        """Create OllamaBackend with mocked client."""
        with patch('httpx.Client') as mock_client:
            backend = OllamaBackend(mock_settings)
            backend._client = mock_client
            return backend

    def test_chat_non_streaming_success(self, ollama_backend: OllamaBackend):
        """Test successful non-streaming chat."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "Test response", "tool_calls": None}
        }
        ollama_backend._client.post.return_value = mock_response

        messages = [{"role": "user", "content": "Hello"}]
        responses = list(ollama_backend.chat(messages, "test-model", stream=False))

        assert len(responses) == 1
        assert responses[0].content == "Test response"
        assert responses[0].done is True

    def test_chat_streaming_success(self, ollama_backend: OllamaBackend):
        """Test successful streaming chat."""
        mock_resp = MagicMock()
        mock_resp.iter_lines.return_value = [
            '{"message": {"content": "Chunk1"}}',
            '{"message": {"content": "Chunk2"}, "done": true}'
        ]
        ollama_backend._client.stream.return_value.__enter__.return_value = mock_resp

        messages = [{"role": "user", "content": "Hello"}]
        responses = list(ollama_backend.chat(messages, "test-model", stream=True))

        assert len(responses) == 3  # Two chunks + final
        assert responses[0].content == "Chunk1"
        assert responses[1].content == "Chunk2"
        assert responses[2].content == "Chunk1Chunk2"
        assert responses[2].done is True

    def test_chat_http_error(self, ollama_backend: OllamaBackend):
        """Test HTTP error handling in chat."""
        from httpx import HTTPError
        ollama_backend._client.post.side_effect = HTTPError("Test error")

        messages = [{"role": "user", "content": "Hello"}]
        with pytest.raises(HTTPError):
            list(ollama_backend.chat(messages, "test-model", stream=False))

    def test_is_available_success(self, ollama_backend: OllamaBackend):
        """Test availability check success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        ollama_backend._client.get.return_value = mock_response

        assert ollama_backend.is_available() is True

    def test_is_available_failure(self, ollama_backend: OllamaBackend):
        """Test availability check failure."""
        ollama_backend._client.get.side_effect = Exception("Connection failed")

        assert ollama_backend.is_available() is False

    def test_get_models_success(self, ollama_backend: OllamaBackend):
        """Test successful model listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "model1"}, {"name": "model2"}]}
        ollama_backend._client.get.return_value = mock_response

        models = ollama_backend.get_models()
        assert models == ["model1", "model2"]

    def test_get_models_failure(self, ollama_backend: OllamaBackend):
        """Test model listing failure."""
        ollama_backend._client.get.side_effect = Exception("API error")

        models = ollama_backend.get_models()
        assert models == []


class TestLlamaCppBackend:
    """Tests for LlamaCppBackend class."""

    @pytest.fixture
    def llamacpp_backend(self, mock_settings: Settings) -> LlamaCppBackend:
        """Create LlamaCppBackend with mocked server."""
        with patch('agent.core.llamacpp_server.LlamaCppServer') as mock_server_class:
            mock_server = MagicMock()
            mock_server.is_running.return_value = True
            mock_server_class.return_value = mock_server

            with patch('httpx.Client') as mock_client:
                backend = LlamaCppBackend(mock_settings)
                backend._client = mock_client
                return backend

    def test_init_ensures_server(self, mock_settings: Settings):
        """Test initialization ensures server is running."""
        with patch('agent.core.backend_manager.LlamaCppServer') as mock_server_class:
            mock_server = MagicMock()
            mock_server.is_running.return_value = False
            mock_server_class.return_value = mock_server

            with patch('httpx.Client'):
                backend = LlamaCppBackend(mock_settings)
                mock_server.start.assert_called_once()

    def test_chat_non_streaming_success(self, llamacpp_backend: LlamaCppBackend):
        """Test successful non-streaming chat."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response", "tool_calls": None}}]
        }
        llamacpp_backend._client.post.return_value = mock_response

        messages = [{"role": "user", "content": "Hello"}]
        responses = list(llamacpp_backend.chat(messages, "test-model", stream=False))

        assert len(responses) == 1
        assert responses[0].content == "Test response"
        assert responses[0].done is True

    def test_chat_streaming_success(self, llamacpp_backend: LlamaCppBackend):
        """Test successful streaming chat."""
        mock_resp = MagicMock()
        mock_resp.iter_lines.return_value = [
            'data: {"choices": [{"delta": {"content": "Chunk1"}}]}',
            'data: {"choices": [{"delta": {"content": "Chunk2"}, "finish_reason": "stop"}]}'
        ]
        llamacpp_backend._client.stream.return_value.__enter__.return_value = mock_resp

        messages = [{"role": "user", "content": "Hello"}]
        responses = list(llamacpp_backend.chat(messages, "test-model", stream=True))

        assert len(responses) == 3  # Two chunks + final
        assert responses[0].content == "Chunk1"
        assert responses[1].content == "Chunk2"
        assert responses[2].content == "Chunk1Chunk2"
        assert responses[2].done is True

    def test_is_available(self, llamacpp_backend: LlamaCppBackend):
        """Test availability check."""
        assert llamacpp_backend.is_available() is True

        llamacpp_backend.server = None
        assert llamacpp_backend.is_available() is False

    def test_get_models(self, mock_settings: Settings):
        """Test model listing."""
        with patch('agent.core.llamacpp_server.LlamaCppServer'):
            with patch('httpx.Client'):
                backend = LlamaCppBackend(mock_settings)
                models = backend.get_models()
                assert models == ["./test-model.gguf"]

    def test_shutdown(self, llamacpp_backend: LlamaCppBackend):
        """Test server shutdown."""
        llamacpp_backend.shutdown()
        llamacpp_backend.server.stop.assert_called_once()


class TestGetBackend:
    """Tests for get_backend factory function."""

    def test_get_ollama_backend(self, mock_settings: Settings):
        """Test getting Ollama backend."""
        mock_settings.backend = "ollama"
        with patch('httpx.Client'):
            backend = get_backend(mock_settings)
            assert isinstance(backend, OllamaBackend)

    def test_get_llamacpp_backend(self, mock_settings: Settings):
        """Test getting LlamaCpp backend."""
        mock_settings.backend = "llamacpp"
        with patch('agent.core.llamacpp_server.LlamaCppServer'):
            with patch('httpx.Client'):
                backend = get_backend(mock_settings)
                assert isinstance(backend, LlamaCppBackend)

    def test_get_unknown_backend(self, mock_settings: Settings):
        """Test unknown backend raises ValueError."""
        mock_settings.backend = "unknown"
        with pytest.raises(ValueError, match="Unknown backend"):
            get_backend(mock_settings)