"""The database connection.

The address and password come from an environment variable (locally from a
git-ignored `.env`, in Colab from a Colab secret). They are never written in the
code and never printed: SQLAlchemy shows the password as *** in its messages.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

ENV_VAR = "DATABASE_URL"


def normalize_url(url: str) -> str:
    """Neon gives `postgresql://...`; SQLAlchemy needs to know the driver (psycopg)."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def database_url(env_var: str = ENV_VAR) -> str:
    url = os.environ.get(env_var)
    if not url:
        raise RuntimeError(
            f"Set {env_var} to the ingest_svc connection string. Never commit or print it."
        )
    return normalize_url(url)


def get_engine(url: str | None = None) -> Engine:
    return create_engine(normalize_url(url) if url else database_url(), pool_pre_ping=True)
