from __future__ import annotations

import pytest

from gov_oracle_agents.config import Settings
from gov_oracle_agents.storage import reset_engine


@pytest.fixture()
def settings(tmp_path) -> Settings:
    """Isolated file-backed SQLite DB per test, crawling disabled."""
    reset_engine()
    s = Settings()
    s.database_url = f"sqlite:///{tmp_path}/test.db"
    s.openai_api_key = ""
    s.crawl_enabled = False
    yield s
    reset_engine()
