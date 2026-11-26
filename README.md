# PetrIA-Ingest

Data pipeline: reads the official Argentine well files, cleans them, and loads them
into the `geo` schema (Postgres + PostGIS).

Part of **[PetrIA](https://github.com/Toti-Gauna/PetrIA)**: a map of the Vaca
Muerta wells with a heat map of expected productivity, plus an AI assistant.
PetrIA estimates productivity from existing wells. It does not discover oil,
and it is not drilling or investment advice.

Data: Secretaría de Energía (Capítulo IV registry). The license is not specified,
so PetrIA is a non-commercial demo that cites the source (ADR-0005). The data
files are **never** committed.

## Status
Version 1.0, batch 1.1a: the **well registry** loads into `geo.wells` (one row per
physical well, `sigla`) and `geo.well_records` (one row per `idpozo`), with a
quality report. Production and fracturing come in 1.1b.

## Layout
```
src/petria_ingest/
  geo_points.py     Argentina box; fix swapped points (ok / swapped_fixed / invalid)
  well_index.py     hash map idpozo -> sigla (algorithm spot, AI-assisted)
  registry.py       read and clean the registry CSV
  load.py           quality report, fingerprint, idempotent load (COPY + upsert)
  migrate.py        run the migrations (Alembic) as ingest_svc
  migrations/       0001: geo.load_runs, geo.wells, geo.well_records
notebooks/
  10_load_registry.ipynb   Colab runner: upload the file, read the report, load
tests/              pytest; fixtures are SYNTHETIC
docs/cleaning-rules.md     every cleaning rule, and what we never do
```

## Load the real file (Colab, works from a tablet)
Open [`notebooks/10_load_registry.ipynb`](https://colab.research.google.com/github/Toti-Gauna/PetrIA-Ingest/blob/main/notebooks/10_load_registry.ipynb)
and follow the cells. It needs one Colab secret, `PETRIA_INGEST_URL`: the
`ingest_svc` connection string.

## Develop and test
```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
```
The database tests need a Postgres with PostGIS and the 0.2 roles (PetrIA repo,
`infra/postgres/`) and two variables, `TEST_INGEST_URL` (ingest_svc) and
`TEST_ML_URL` (ml_svc). Without them they are skipped. CI runs them on Postgres 18.

## Configuration
Copy `.env.example` to `.env` and fill in the values. Never commit `.env`.
