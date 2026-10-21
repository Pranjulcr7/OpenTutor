import json
import stat
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from config import settings
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from services.llm.local_config import update_llm_runtime_config


@pytest.fixture
def local_config(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    monkeypatch.setenv("LOCAL_ENV_FILE", str(path))
    monkeypatch.setattr(settings, "deployment_mode", "single_user")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "llm_model", "fixture")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("LLM_MODEL", "fixture")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    return path


def test_secret_round_trip_never_returns_fragments(local_config):
    from dotenv import dotenv_values

    secret = "sk-fixture'with#punctuation"
    result = update_llm_runtime_config({"provider_keys": {"openai": secret}})
    assert dotenv_values(local_config)["OPENAI_API_KEY"] == secret
    assert stat.S_IMODE(local_config.stat().st_mode) == 0o600
    assert secret not in json.dumps(result)
    assert (
        next(p for p in result["providers"] if p["provider"] == "openai")["masked_key"]
        == "********"
    )
    update_llm_runtime_config({"provider_keys": {"openai": ""}})
    assert "OPENAI_API_KEY" not in dotenv_values(local_config)


@pytest.mark.parametrize(
    "payload",
    [
        {"model": "model\nAUTH_ENABLED=false"},
        {"provider_keys": {"openai": "secret\nINJECTED=1"}},
        {"base_url": "https://user:secret@example.com"},
        {"base_url": "file:///etc/passwd"},
    ],
)
def test_invalid_config_cannot_write_env(local_config, payload):
    with pytest.raises(ValueError):
        update_llm_runtime_config(payload)
    assert not local_config.exists()


def test_global_config_blocked_in_multiuser(local_config, monkeypatch):
    from routers.preferences_llm import require_single_user_config

    monkeypatch.setattr(settings, "deployment_mode", "multi_user")
    with pytest.raises(HTTPException) as error:
        require_single_user_config()
    assert error.value.status_code == 403
    with pytest.raises(ValueError):
        update_llm_runtime_config({"model": "other"})
    assert not local_config.exists()


@pytest.mark.asyncio
async def test_validation_response_does_not_echo_key():
    from main import safe_validation_error_handler

    error = RequestValidationError(
        [
            {
                "loc": ("body", "api_key"),
                "type": "string_type",
                "input": {"key": "private-secret"},
                "msg": "private-secret",
            }
        ]
    )
    result = await safe_validation_error_handler(None, error)
    assert result.status_code == 422
    assert b"private-secret" not in result.body


@pytest.mark.asyncio
async def test_connection_error_sanitized():
    from libs.exceptions import ExternalServiceError
    from routers.preferences_llm import test_runtime_llm_config
    from schemas.preference import LlmConnectionTestRequest

    with patch(
        "routers.preferences_llm.test_llm_connection",
        new=AsyncMock(side_effect=RuntimeError("private-secret")),
    ):
        with pytest.raises(ExternalServiceError) as error:
            await test_runtime_llm_config(
                LlmConnectionTestRequest(
                    provider="openai", model="fixture", api_key="private-secret"
                ),
                SimpleNamespace(),
            )
        assert "private-secret" not in str(error.value)
