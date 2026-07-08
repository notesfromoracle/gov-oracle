"""Entry point: `python wsgi.py` (dev) or `gunicorn wsgi:app` (prod)."""
from src.app import create_app

app = create_app()

if __name__ == "__main__":
    import os

    app.run(host="0.0.0.0", port=int(os.getenv("FLASK_PORT", "5001")), debug=True)
