"""Fail-fast configuration validation for production entry points."""
from __future__ import annotations

import pytest

from gov_oracle_agents.config import ConfigError, validate_required_config


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("DATABASE_URL", "OPENAI_API_KEY", "ALLOW_MISSING_CONFIG"):
        monkeypatch.delenv(var, raising=False)


def test_raises_and_names_all_missing_vars():
    with pytest.raises(ConfigError) as exc:
        validate_required_config()
    message = str(exc.value)
    assert "DATABASE_URL" in message
    assert "OPENAI_API_KEY" in message
    # the error must self-diagnose the .env search so a broken server explains itself
    assert "dotenv search" in message
    assert "cwd" in message


def test_passes_when_both_set(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://u:p@localhost/db")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    validate_required_config()  # no raise


def test_llm_key_optional_when_not_required(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://u:p@localhost/db")
    validate_required_config(require_llm=False)  # no raise
    with pytest.raises(ConfigError):
        validate_required_config(require_llm=True)


def test_dev_bypass(monkeypatch):
    monkeypatch.setenv("ALLOW_MISSING_CONFIG", "true")
    validate_required_config()  # no raise even with nothing set
