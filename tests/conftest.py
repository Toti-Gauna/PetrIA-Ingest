"""Database fixtures for the load tests.

They need a test Postgres with PostGIS and the 0.2 roles (PetrIA repo,
infra/postgres/init/02-schemas-and-roles.sql), and two connection strings:
  TEST_INGEST_URL  the ingest_svc login (runs migrations and loads)
  TEST_ML_URL      the ml_svc login (a reader, to prove the walls)
Without them, the database tests are skipped (the other tests still run).
CI provides both; see .github/workflows/ci.yml.
"""

import os

import pytest
from sqlalchemy import create_engine, text

from petria_ingest import migrate
from petria_ingest.db import normalize_url

INGEST_URL = os.environ.get("TEST_INGEST_URL")
ML_URL = os.environ.get("TEST_ML_URL")

needs_db = pytest.mark.skipif(
    not (INGEST_URL and ML_URL),
    reason="set TEST_INGEST_URL and TEST_ML_URL (a test Postgres with the 0.2 roles)",
)


@pytest.fixture(scope="session")
def ingest_engine():
    migrate.downgrade_all(INGEST_URL)  # start from nothing: proves downgrade works too
    migrate.upgrade(INGEST_URL)
    engine = create_engine(normalize_url(INGEST_URL))
    yield engine
    engine.dispose()


@pytest.fixture
def empty_geo(ingest_engine):
    with ingest_engine.begin() as conn:
        conn.execute(text("TRUNCATE geo.well_records, geo.wells, geo.load_runs RESTART IDENTITY"))
    return ingest_engine


@pytest.fixture(scope="session")
def ml_engine():
    engine = create_engine(normalize_url(ML_URL))
    yield engine
    engine.dispose()
