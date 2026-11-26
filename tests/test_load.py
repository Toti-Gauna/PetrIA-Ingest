from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from petria_ingest import load as load_module
from petria_ingest import migrate
from petria_ingest.load import load_registry

from .conftest import ML_URL, needs_db

FIXTURE = Path(__file__).parent / "fixtures" / "registry_synthetic.csv"

pytestmark = needs_db


def _counts(engine):
    with engine.connect() as c:
        return (
            c.execute(text("SELECT count(*) FROM geo.wells")).scalar(),
            c.execute(text("SELECT count(*) FROM geo.well_records")).scalar(),
            c.execute(text("SELECT count(*) FROM geo.load_runs WHERE status = 'done'")).scalar(),
        )


def test_tables_are_owned_by_ingest_svc_and_alembic_lives_in_geo(ingest_engine):
    with ingest_engine.connect() as c:
        owners = dict(
            c.execute(
                text("SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'geo'")
            ).all()
        )
    assert owners["wells"] == owners["well_records"] == owners["load_runs"] == "ingest_svc"
    assert "alembic_version" in owners  # Alembic's memory, inside geo


def test_migrations_refuse_any_other_login():
    with pytest.raises(RuntimeError, match="must run as ingest_svc"):
        migrate.upgrade(ML_URL)


def test_load_writes_wells_records_and_a_load_run(empty_geo):
    result = load_registry(FIXTURE, empty_geo)
    assert result["status"] == "done"
    assert _counts(empty_geo) == (6, 7, 1)
    with empty_geo.connect() as c:
        point = "SELECT ST_X(geom), ST_Y(geom), ST_SRID(geom) FROM geo.wells WHERE sigla = :s"
        x, y, srid = c.execute(text(point), {"s": "SYN-B-2"}).one()
        assert (round(x, 2), round(y, 2), srid) == (-69.42, -38.59, 4326)  # swapped, fixed
        no_point = "SELECT geom FROM geo.wells WHERE sigla = :s"
        assert c.execute(text(no_point), {"s": "SYN-D-4"}).scalar() is None
        sha, report = c.execute(text("SELECT file_sha256, report FROM geo.load_runs")).one()
        assert sha == load_module.file_sha256(FIXTURE)
        assert report["records"] == 7


def test_the_same_file_twice_is_skipped_and_changes_nothing(empty_geo):
    load_registry(FIXTURE, empty_geo)
    second = load_registry(FIXTURE, empty_geo)
    assert second["status"] == "skipped"
    assert _counts(empty_geo) == (6, 7, 1)


def test_forced_reload_updates_rows_but_never_duplicates(empty_geo):
    load_registry(FIXTURE, empty_geo)
    again = load_registry(FIXTURE, empty_geo, force=True)
    assert again["status"] == "done"
    assert _counts(empty_geo) == (6, 7, 2)  # two loads recorded, rows not duplicated


def test_a_failed_load_saves_nothing(empty_geo, monkeypatch):
    real_clean = load_module.clean_registry

    def broken_clean(df):
        clean = real_clean(df)
        clean.records[-1]["location_flag"] = "bogus"  # violates the table's CHECK rule
        return clean

    monkeypatch.setattr(load_module, "clean_registry", broken_clean)
    with pytest.raises(DBAPIError):
        load_registry(FIXTURE, empty_geo)
    assert _counts(empty_geo) == (0, 0, 0)  # all or nothing


def test_readers_can_read_the_new_tables_but_never_write(empty_geo, ml_engine):
    load_registry(FIXTURE, empty_geo)
    with ml_engine.connect() as c:  # ml_svc: a reader of geo (0.2 default privileges)
        assert c.execute(text("SELECT count(*) FROM geo.wells")).scalar() == 6
    with ml_engine.connect() as c, pytest.raises(DBAPIError) as err:
        c.execute(text("INSERT INTO geo.load_runs (source, file_name, file_sha256, status) "
                       "VALUES ('x', 'x', 'x', 'done')"))  # fmt: skip
    assert err.value.orig.sqlstate == "42501"  # insufficient_privilege
