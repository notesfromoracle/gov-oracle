from __future__ import annotations

from flask import Blueprint, jsonify, request

from . import cache, db, jobs

api = Blueprint("api", __name__, url_prefix="/api")


@api.get("/health")
def health():
    return jsonify({"status": "ok"})


@api.get("/governments")
def governments():
    return jsonify(db.list_governments())


@api.get("/governments/<int:government_id>")
def government(government_id: int):
    gov = db.get_government(government_id)
    if gov is None:
        return jsonify({"error": "government not found"}), 404
    return jsonify(gov)


@api.get("/governments/<int:government_id>/latest-report")
def latest_report(government_id: int):
    key = cache.latest_report_key(government_id)
    cached = cache.get_cached(key)
    if cached is not None:
        return jsonify(cached)
    report = db.get_latest_report(government_id)
    if report is None:
        return jsonify({"error": "no report yet", "government_id": government_id}), 404
    cache.set_cached(key, report)
    return jsonify(report)


@api.get("/governments/<int:government_id>/reports")
def reports(government_id: int):
    return jsonify(db.list_reports(government_id))


@api.get("/reports/<int:report_id>")
def report(report_id: int):
    payload = db.get_report(report_id)
    if payload is None:
        return jsonify({"error": "report not found"}), 404
    return jsonify(payload)


@api.post("/governments/<int:government_id>/run")
def trigger_run(government_id: int):
    name = db.get_government_name(government_id)
    if name is None:
        return jsonify({"error": "government not found"}), 404
    run_type = (request.get_json(silent=True) or {}).get("run_type", "manual")
    if run_type not in ("daily", "weekly", "manual"):
        return jsonify({"error": "run_type must be daily, weekly, or manual"}), 400
    result = jobs.enqueue_run(name, run_type)
    return jsonify(result), 202


@api.get("/governments/<int:government_id>/scores/history")
def scores_history(government_id: int):
    return jsonify(db.score_history(government_id))


@api.get("/governments/<int:government_id>/sources")
def sources(government_id: int):
    return jsonify(db.list_sources(government_id))


@api.get("/governments/<int:government_id>/failed-questions")
def failed_questions(government_id: int):
    return jsonify(db.latest_failed_questions(government_id))
