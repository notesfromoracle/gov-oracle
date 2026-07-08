"""Runtime configuration, read from environment variables.

The library must work in three modes:
  1. Full: MySQL + Redis + LLM key (production).
  2. Local: SQLite fallback, no Redis, rule-based analyst (demo/dev).
  3. Test: in-memory SQLite, network disabled.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

DEFAULT_SQLITE_URL = "sqlite:///./gov_oracle.db"


@dataclass
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)
    )
    redis_url: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    )
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_api_base: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    )
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    crawl_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("CRAWL_TIMEOUT_SECONDS", "20"))
    )
    crawl_max_sources: int = field(
        default_factory=lambda: int(os.getenv("CRAWL_MAX_SOURCES", "100"))
    )
    crawl_user_agent: str = field(
        default_factory=lambda: os.getenv(
            "CRAWL_USER_AGENT",
            "GovOracleBot/0.1 (public-information audit)",
        )
    )
    crawl_enabled: bool = field(
        default_factory=lambda: os.getenv("CRAWL_ENABLED", "true").lower() != "false"
    )
    # Deep-crawl breadth controls. depth 0 = root pages only (old behavior).
    crawl_depth: int = field(default_factory=lambda: int(os.getenv("CRAWL_DEPTH", "1")))
    crawl_max_links_per_source: int = field(
        default_factory=lambda: int(os.getenv("CRAWL_MAX_LINKS_PER_SOURCE", "5"))
    )
    crawl_max_pages_total: int = field(
        default_factory=lambda: int(os.getenv("CRAWL_MAX_PAGES_TOTAL", "80"))
    )
    # Headless-browser fallback for bot-walled / JS-rendered sites. Requires
    # the "full" extra (playwright) + `playwright install chromium`; silently
    # skipped when unavailable.
    crawl_use_browser: bool = field(
        default_factory=lambda: os.getenv("CRAWL_USE_BROWSER", "true").lower() != "false"
    )


def get_settings() -> Settings:
    return Settings()
