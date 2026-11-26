"""Load the cleaned registry into geo, idempotently, with a record of every load.

- inspect_registry(path): clean the file and return the quality report. No database.
- load_registry(path, engine): the same, then write to geo in ONE transaction:
  either everything is saved or nothing is.

Idempotent in two ways:
1. The file's fingerprint (SHA-256 of its bytes) is stored in geo.load_runs. The same
   file is not loaded twice unless force=True.
2. Every row is an upsert: loading again updates rows, it never duplicates them.

Fast over the internet (Colab -> Neon): rows are streamed with one COPY into a
temporary table, then ONE upsert statement per table. A few round trips in total,
instead of one per row (164,000 for the real registry).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from psycopg import sql
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from .registry import TEXT_COLUMNS, clean_registry, read_registry

SOURCE = "registry"

_POINT = "CASE WHEN lon IS NULL THEN NULL ELSE ST_SetSRID(ST_MakePoint(lon, lat), 4326) END"

# Column names come from our own constant list, never from the file.
_TEXT_DEFS = ", ".join(f"{c} text" for c in TEXT_COLUMNS)
_TEXT_COLS = ", ".join(TEXT_COLUMNS)
_TEXT_SETS = ",\n  ".join(f"{c} = EXCLUDED.{c}" for c in TEXT_COLUMNS)

WELL_COLUMNS = ["sigla", "lon", "lat", "location_flag", "n_records"]
RECORD_COLUMNS = ["idpozo", "sigla", *TEXT_COLUMNS, "lon", "lat", "location_flag"]

STAGE_SQL = f"""
CREATE TEMP TABLE stage_wells (
  sigla text, lon double precision, lat double precision,
  location_flag text, n_records integer
) ON COMMIT DROP;
CREATE TEMP TABLE stage_records (
  idpozo bigint, sigla text, {_TEXT_DEFS},
  lon double precision, lat double precision, location_flag text
) ON COMMIT DROP;
"""

UPSERT_WELLS = f"""
INSERT INTO geo.wells (sigla, geom, location_flag, n_records, load_id)
SELECT sigla, {_POINT}, location_flag, n_records, :load_id FROM stage_wells
ON CONFLICT (sigla) DO UPDATE SET
  geom = EXCLUDED.geom,
  location_flag = EXCLUDED.location_flag,
  n_records = EXCLUDED.n_records,
  load_id = EXCLUDED.load_id
"""

UPSERT_RECORDS = f"""
INSERT INTO geo.well_records (idpozo, sigla, {_TEXT_COLS}, geom, location_flag, load_id)
SELECT idpozo, sigla, {_TEXT_COLS}, {_POINT}, location_flag, :load_id FROM stage_records
ON CONFLICT (idpozo) DO UPDATE SET
  sigla = EXCLUDED.sigla,
  {_TEXT_SETS},
  geom = EXCLUDED.geom,
  location_flag = EXCLUDED.location_flag,
  load_id = EXCLUDED.load_id
"""


def file_sha256(path: str | Path) -> str:
    """The file's fingerprint: same bytes, same code; one byte changed, another code."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy(conn: Connection, table: str, columns: list[str], rows: list[dict]) -> None:
    """Stream rows into a staging table with COPY (values travel as data, never as SQL).

    Table and column names are quoted by the driver (sql.Identifier), so even our own
    constants never get glued into the command as raw text.
    """
    statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
        sql.Identifier(table), sql.SQL(", ").join(sql.Identifier(c) for c in columns)
    )
    cursor = conn.connection.driver_connection.cursor()
    with cursor.copy(statement) as copy:
        for row in rows:
            copy.write_row([row[c] for c in columns])


def inspect_registry(path: str | Path) -> dict:
    """Clean the file and return the report. Touches no database."""
    df, meta = read_registry(path)
    clean = clean_registry(df)
    return {"file_name": Path(path).name, "file_sha256": file_sha256(path), **meta, **clean.report}


def load_registry(path: str | Path, engine: Engine, *, force: bool = False) -> dict:
    path = Path(path)
    sha = file_sha256(path)
    df, meta = read_registry(path)
    clean = clean_registry(df)
    report = {"file_name": path.name, "file_sha256": sha, **meta, **clean.report}

    with engine.begin() as conn:  # one transaction: all or nothing
        already = conn.execute(
            text(
                "SELECT id FROM geo.load_runs WHERE source = :s AND file_sha256 = :h "
                "AND status = 'done' ORDER BY id DESC LIMIT 1"
            ),
            {"s": SOURCE, "h": sha},
        ).scalar()
        if already and not force:
            return {"status": "skipped", "reason": "this exact file was already loaded",
                    "load_id": already, "report": report}  # fmt: skip

        load_id = conn.execute(
            text(
                "INSERT INTO geo.load_runs (source, file_name, file_sha256, status) "
                "VALUES (:s, :f, :h, 'running') RETURNING id"
            ),
            {"s": SOURCE, "f": path.name, "h": sha},
        ).scalar_one()

        conn.exec_driver_sql(STAGE_SQL)
        _copy(conn, "stage_wells", WELL_COLUMNS, clean.wells)
        _copy(conn, "stage_records", RECORD_COLUMNS, clean.records)
        # Wells first: every record points to its well.
        conn.execute(text(UPSERT_WELLS), {"load_id": load_id})
        conn.execute(text(UPSERT_RECORDS), {"load_id": load_id})

        conn.execute(
            text(
                "UPDATE geo.load_runs SET status = 'done', finished_at = now(), "
                "rows_read = :read, rows_loaded = :loaded, report = CAST(:report AS jsonb) "
                "WHERE id = :id"
            ),
            {
                "read": clean.report["rows_read"],
                "loaded": len(clean.records),
                "report": json.dumps(report, ensure_ascii=False, default=str),
                "id": load_id,
            },
        )
    return {"status": "done", "load_id": load_id, "report": report}


def report_lines(report: dict) -> list[str]:
    """The quality report as short readable lines (for the notebook)."""
    r = report
    flags = r.get("record_location_flags", {})
    return [
        f"File: {r.get('file_name')}  ({r.get('encoding')}, {r.get('delimiter')} separated)",
        f"Fingerprint: {r.get('file_sha256')}",
        f"Rows read: {r['rows_read']}  |  rejected: {r['rows_rejected']}",
        f"Records (idpozo): {r['records']}  |  wells (sigla): {r['wells']}  |  "
        f"wells with several records: {r['wells_with_several_records']}",
        f"  of them, with different formations: {r['wells_with_several_formations']}  "
        f"e.g. {r['wells_with_several_formations_sample']}",
        f"  of them, with a record missing its formacion: "
        f"{r['wells_with_a_record_missing_formacion']}",
        f"Locations (records): ok {flags.get('ok', 0)}, swapped_fixed "
        f"{flags.get('swapped_fixed', 0)}, invalid {flags.get('invalid', 0)}",
        f"Locations (wells): {r['well_location_flags']}",
        f"Point problems: {r['geojson_problems']}  |  wells with points >100 m apart: "
        f"{r['wells_with_points_far_apart']}",
        f"Records with formacion 'vaca muerta': {r['records_formacion_vaca_muerta']}",
        f"Duplicate idpozo rows: {r['duplicate_idpozo_rows']}  |  sigla trimmed: "
        f"{r['sigla_whitespace_trimmed']}  |  extra columns: {r.get('extra_columns')}",
    ]
