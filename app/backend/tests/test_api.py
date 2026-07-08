"""API tests against an isolated SQLite DB seeded by an offline oracle run."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "api_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["CRAWL_ENABLED"] = "false"
    os.environ["SCHEDULER_ENABLED"] = "false"
    os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"  # deliberately unreachable

    from gov_oracle_agents import GovernmentOracle
    from gov_oracle_agents.storage import reset_engine

    reset_engine()
    GovernmentOracle().run_government_report("Government of Bangladesh")

    from src.app import create_app

    app = create_app()
    app.testing = True
    with app.test_client() as test_client:
        yield test_client
    reset_engine()


def test_health(client):
    assert client.get("/api/health").json["status"] == "ok"


def test_list_governments(client):
    body = client.get("/api/governments").json
    assert len(body) == 1
    assert body[0]["name"] == "Government of Bangladesh"
    assert body[0]["latest_report"]["overall_score"] is not None


def test_government_detail_and_404(client):
    gov = client.get("/api/governments/1")
    assert gov.status_code == 200
    assert gov.json["country_code"] == "BD"
    assert client.get("/api/governments/999").status_code == 404


def test_latest_report(client):
    body = client.get("/api/governments/1/latest-report").json
    assert body["government"] == "Government of Bangladesh"
    assert "transparency_scores" in body
    assert "score_explanations" in body
    assert body["stale"] is False


def test_reports_list_and_detail(client):
    reports = client.get("/api/governments/1/reports").json
    assert len(reports) >= 1
    report_id = reports[0]["id"]
    detail = client.get(f"/api/reports/{report_id}").json
    assert detail["report_id"] == report_id
    assert "failed_questions" in detail


def test_score_history(client):
    history = client.get("/api/governments/1/scores/history").json
    assert len(history) >= 1
    assert set(history[0]) >= {
        "documentation", "timeliness", "accessibility",
        "completeness", "traceability", "explainability", "overall",
    }


def test_sources(client):
    sources = client.get("/api/governments/1/sources").json
    assert len(sources) >= 10
    assert all("url" in s for s in sources)


def test_failed_questions(client):
    questions = client.get("/api/governments/1/failed-questions").json
    assert len(questions) > 0
    failed = [q for q in questions if q["status"] == "failed"]
    assert all(q["missing_data"] for q in failed)


def test_trigger_run_returns_202(client):
    response = client.post("/api/governments/1/run", json={"run_type": "manual"})
    assert response.status_code == 202
    assert response.json["queued"] is True
    assert client.post("/api/governments/1/run", json={"run_type": "bogus"}).status_code == 400
    assert client.post("/api/governments/999/run").status_code == 404
