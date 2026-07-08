"""Redis-backed report cache with graceful degradation.

If Redis is unavailable the API still works — it just reads from the
database every time. Cache keys are invalidated after each agent run.
"""
from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60 * 60 * 6  # latest reports refresh at most daily


def _client():
    try:
        import redis

        client = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
            socket_connect_timeout=1,
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception:
        return None


def get_cached(key: str) -> dict | None:
    client = _client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.debug("cache read failed: %s", exc)
        return None


def set_cached(key: str, value: dict) -> None:
    client = _client()
    if client is None:
        return
    try:
        client.setex(key, CACHE_TTL_SECONDS, json.dumps(value, default=str))
    except Exception as exc:
        logger.debug("cache write failed: %s", exc)


def invalidate(key: str) -> None:
    client = _client()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception as exc:
        logger.debug("cache invalidate failed: %s", exc)


def latest_report_key(government_id: int) -> str:
    return f"gov_oracle:latest_report:{government_id}"
