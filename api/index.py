"""Vercel serverless entrypoint — imports the FastAPI app.

Usage: deploy this repo to Vercel with the Python runtime. Set SECRET_KEY
(and DATABASE_URL to Postgres for persistence; SQLite uses /tmp which is
ephemeral per serverless instance).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Vercel serverless: use an ephemeral SQLite in /tmp unless DATABASE_URL is set
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "sqlite:////tmp/imdaad.db"

from app.main import app  # noqa: E402

handler = app
