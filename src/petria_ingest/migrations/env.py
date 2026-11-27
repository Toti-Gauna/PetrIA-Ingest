"""Alembic's entry point: how to connect, and where to keep its memory."""

import os

from alembic import context
from sqlalchemy import create_engine, pool, text

from petria_ingest.db import database_url, normalize_url

config = context.config
EXPECTED_ROLE = os.environ.get("PETRIA_MIGRATION_ROLE", "ingest_svc")


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url") or database_url()
    engine = create_engine(normalize_url(url), poolclass=pool.NullPool)
    with engine.connect() as connection:
        who = connection.execute(text("SELECT current_user")).scalar()
        # End the transaction this check opened. Otherwise Alembic thinks someone else
        # owns the transaction, never commits, and every change is rolled back.
        connection.commit()
        if who != EXPECTED_ROLE:
            raise RuntimeError(
                f"Migrations must run as {EXPECTED_ROLE}, not {who}: the creator owns the "
                "tables, and only tables created by ingest_svc are readable by the "
                "readers (ADR-0012)."
            )
        context.configure(
            connection=connection,
            target_metadata=None,
            version_table_schema="geo",  # ingest_svc may not create tables in public
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Offline mode is not used in PetrIA: run against a database.")
run_migrations_online()
