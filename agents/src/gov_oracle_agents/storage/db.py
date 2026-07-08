"""Engine/session management with lazy initialization."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings
from .orm import Base

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine(database_url: str | None = None) -> Engine:
    global _engine, _session_factory
    if _engine is None or database_url is not None:
        url = database_url or get_settings().database_url
        kwargs: dict = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **kwargs)
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def init_db(database_url: str | None = None) -> Engine:
    """Create all tables if missing. Idempotent; used by the CLI and tests.

    Production deployments should use Alembic migrations instead.
    """
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    _ensure_question_answer_columns(engine)
    return engine


def _ensure_question_answer_columns(engine: Engine) -> None:
    """Lightweight forward-fix for pre-existing dev databases.

    create_all() never alters existing tables, so databases created before
    answer synthesis lack the new failed_questions columns. ADD COLUMN is
    identical on MySQL and SQLite for these types. Production should apply
    Alembic migration 0002 instead; this keeps dev/demo DBs working.
    """
    from sqlalchemy import inspect, text

    existing = {col["name"] for col in inspect(engine).get_columns("failed_questions")}
    additions = {
        "answer": "TEXT",
        "findings_json": "JSON",
        "evidence_json": "JSON",
        "confidence": "FLOAT",
    }
    with engine.begin() as connection:
        for column, ddl_type in additions.items():
            if column not in existing:
                connection.execute(
                    text(f"ALTER TABLE failed_questions ADD COLUMN {column} {ddl_type}")
                )


@contextmanager
def session_scope(database_url: str | None = None) -> Iterator[Session]:
    get_engine(database_url)
    assert _session_factory is not None
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """Used by tests to swap databases."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
