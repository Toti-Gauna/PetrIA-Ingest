"""Run the migrations (Alembic) from Python: from Colab, the tests, or a terminal.

Migrations change the STRUCTURE (tables), never load data. Alembic remembers which
ones ran in geo.alembic_version, so each runs once and in order.

They must run as ingest_svc: the creator of a table is its owner, and the 0.2 rule
("tables created by ingest_svc are readable by the readers") only fires for it.
migrations/env.py refuses to run as anyone else.
"""

from importlib.resources import files

from alembic import command
from alembic.config import Config

from .db import database_url, normalize_url


def _config(url: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(files("petria_ingest").joinpath("migrations")))
    # "%" must be doubled for Alembic's config parser (a password could contain one).
    cfg.set_main_option("sqlalchemy.url", normalize_url(url).replace("%", "%%"))
    return cfg


def upgrade(url: str | None = None) -> None:
    """Apply every migration that has not run yet."""
    command.upgrade(_config(url or database_url()), "head")


def downgrade_all(url: str | None = None) -> None:
    """Undo every migration (drops the tables). Used by the tests."""
    command.downgrade(_config(url or database_url()), "base")
