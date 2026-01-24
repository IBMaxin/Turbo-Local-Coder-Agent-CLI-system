"""
Tests for agent/core/config.py edge cases
"""
import pytest
from unittest.mock import patch, mock_open
import os

from agent.core.config import Settings, load_settings, _parse_int_with_validation, _parse_bool, compact_json


class TestSettingsValidation:
    """Tests for Settings validation."""

    def test_settings_custom_values(self):
        """Test Settings accepts custom values."""
        settings = Settings(
            turbo_host="http://custom:8000",
            local_host="http://custom:8001",
            planner_model="custom-planner",
            coder_model="custom-coder",
            api_key="a-very-long-api-key-12345",  # Must be >= 10 chars
            max_steps=50,
            request_timeout_s=600,
            dry_run=True
        )

        assert settings.turbo_host == "http://custom:8000"
        assert settings.max_steps == 50
        assert settings.request_timeout_s == 600
        assert settings.dry_run is True

    def test_settings_equality(self):
        """Test Settings equality comparison."""
        settings1 = Settings(
            turbo_host="http://localhost:8000",
            local_host="http://localhost:8001",
            planner_model="test",
            coder_model="test",
            api_key="a-very-long-api-key-12345",
            max_steps=25,
            request_timeout_s=120,
            dry_run=False
        )
        settings2 = Settings(
            turbo_host="http://localhost:8000",
            local_host="http://localhost:8001",
            planner_model="test",
            coder_model="test",
            api_key="a-very-long-api-key-12345",
            max_steps=25,
            request_timeout_s=120,
            dry_run=False
        )

        assert settings1 == settings2

    def test_settings_inequality(self):
        """Test Settings inequality when values differ."""
        settings1 = Settings(
            turbo_host="http://localhost:8000",
            local_host="http://localhost:8001",
            planner_model="test",
            coder_model="test",
            api_key="a-very-long-api-key-12345",
            max_steps=25,
            request_timeout_s=120,
            dry_run=False
        )
        settings2 = Settings(
            turbo_host="http://other:8000",
            local_host="http://localhost:8001",
            planner_model="test",
            coder_model="test",
            api_key="a-very-long-api-key-12345",
            max_steps=25,
            request_timeout_s=120,
            dry_run=False
        )

        assert settings1 != settings2

    def test_settings_invalid_url(self):
        """Test Settings rejects invalid URLs."""
        with pytest.raises(ValueError, match="Invalid turbo_host URL"):
            Settings(
                turbo_host="invalid-url",
                local_host="http://localhost:8001",
                planner_model="test",
                coder_model="test",
                api_key="a-very-long-api-key-12345",
                max_steps=25,
                request_timeout_s=120,
                dry_run=False
            )

    def test_settings_invalid_max_steps(self):
        """Test Settings rejects invalid max_steps."""
        with pytest.raises(ValueError, match="max_steps must be positive"):
            Settings(
                turbo_host="http://localhost:8000",
                local_host="http://localhost:8001",
                planner_model="test",
                coder_model="test",
                api_key="a-very-long-api-key-12345",
                max_steps=-5,
                request_timeout_s=120,
                dry_run=False
            )

    def test_settings_short_api_key(self):
        """Test Settings rejects short API key."""
        with pytest.raises(ValueError, match="api_key appears to be too short"):
            Settings(
                turbo_host="http://localhost:8000",
                local_host="http://localhost:8001",
                planner_model="test",
                coder_model="test",
                api_key="short",  # Less than 10 chars
                max_steps=25,
                request_timeout_s=120,
                dry_run=False
            )


class TestParseIntWithValidation:
    """Tests for _parse_int_with_validation function."""

    def test_parse_valid_int(self):
        """Test parsing valid integer."""
        result = _parse_int_with_validation("100", "TEST_VALUE")
        assert result == 100

    def test_parse_int_below_min(self):
        """Test parsing integer below minimum."""
        from agent.core.errors import ConfigurationError
        with pytest.raises(ConfigurationError, match="must be >= 1"):
            _parse_int_with_validation("0", "TEST_VALUE", min_value=1)

    def test_parse_invalid_int(self):
        """Test parsing invalid integer."""
        from agent.core.errors import ConfigurationError
        with pytest.raises(ConfigurationError, match="Invalid TEST_VALUE"):
            _parse_int_with_validation("not-a-number", "TEST_VALUE")


class TestParseBool:
    """Tests for _parse_bool function."""

    def test_parse_true_values(self):
        """Test parsing true values."""
        assert _parse_bool("1") is True
        assert _parse_bool("true") is True
        assert _parse_bool("True") is True
        assert _parse_bool("yes") is True
        assert _parse_bool("on") is True

    def test_parse_false_values(self):
        """Test parsing false values."""
        assert _parse_bool("0") is False
        assert _parse_bool("false") is False
        assert _parse_bool("no") is False


class TestCompactJson:
    """Tests for compact_json function."""

    def test_compact_json_dict(self):
        """Test compact JSON for dictionary."""
        result = compact_json({"key": "value", "num": 123})
        assert '"key":"value"' in result
        assert '"num":123' in result

    def test_compact_json_fallback(self):
        """Test compact JSON fallback for unserializable objects."""
        result = compact_json(object())
        assert result == str(object())


class TestSettingsRepr:
    """Tests for Settings repr method."""

    def test_settings_to_dict(self):
        """Test Settings to_dict method."""
        settings = Settings(
            turbo_host="http://localhost:8000",
            local_host="http://localhost:8001",
            planner_model="test",
            coder_model="test",
            api_key="a-very-long-api-key-12345",
            max_steps=25,
            request_timeout_s=120,
            dry_run=False
        )

        result = settings.to_dict()
        assert result['turbo_host'] == "http://localhost:8000"
        assert result['api_key'] == '***'  # Should be masked

    def test_settings_with_overrides(self):
        """Test Settings with_overrides method."""
        settings = Settings(
            turbo_host="http://localhost:8000",
            local_host="http://localhost:8001",
            planner_model="test",
            coder_model="test",
            api_key="a-very-long-api-key-12345",
            max_steps=25,
            request_timeout_s=120,
            dry_run=False
        )

        new_settings = settings.with_overrides(max_steps=50, dry_run=True)
        assert new_settings.max_steps == 50
        assert new_settings.dry_run is True
        assert new_settings.turbo_host == "http://localhost:8000"  # Unchanged
