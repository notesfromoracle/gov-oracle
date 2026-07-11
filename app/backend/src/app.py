from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from . import db
from .routes import api

load_dotenv()
logging.basicConfig(level=logging.INFO)


def create_app() -> Flask:
    from gov_oracle_agents.config import validate_required_config

    validate_required_config()  # abort on missing DATABASE_URL / OPENAI_API_KEY

    app = Flask("gov_oracle_backend")
    # public read API — open CORS by default, restrict via CORS_ORIGINS in prod
    cors_origins = os.getenv("CORS_ORIGINS", "*")
    CORS(app, origins="*" if cors_origins == "*" else cors_origins.split(","))
    db.ensure_schema()
    app.register_blueprint(api)

    from .cli import seed_command

    app.cli.add_command(seed_command)

    if os.getenv("SCHEDULER_ENABLED", "false").lower() == "true":
        from .scheduler import start_scheduler

        start_scheduler()
    return app


def main() -> None:
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("FLASK_PORT", "5001")), debug=True)


if __name__ == "__main__":
    main()
