# Cleaning rules: the well registry (batch 1.1a)

Applies to "Capítulo IV - Pozos" (Secretaría de Energía). Facts marked
**verified** are in `docs/data-sources.md` of the PetrIA repo.

## What we never do
- Invent a value (a location, a well, a date).
- Convert units (`cota`, `profundidad` stay as published text).
- Drop a row silently: every rejected row is counted, with its line number.

## Reading
| Rule | Why |
|---|---|
| Every column is read as text | so `00123` does not become `123` |
| Only an **empty** cell becomes NULL | pandas would otherwise turn the text `NA` or `null` into "missing" |
| Encoding: UTF-8, else Latin-1 (reported) | Argentine files can be either |
| Separator: comma, semicolon or tab, from the header (reported) | not confirmed for every file |
| A missing expected column stops the load | never guess a column |

## Rows
| Case | What happens |
|---|---|
| No `sigla` | rejected, counted, line number kept |
| `idpozo` not a whole number | rejected, counted, line number kept |
| Spaces around `sigla` | trimmed, counted |
| Same `idpozo` twice, same `sigla` | first row kept, counted |
| Same `idpozo` under two `sigla` | **the load stops** (the owner's hash map raises) |

## Locations
Read from `geojson` (longitude first, **verified**), then checked against an
Argentina box (lon -74 to -53, lat -56 to -21.5; a setting in `geo_points.py`).

| Flag | Meaning |
|---|---|
| `ok` | inside the box as published |
| `swapped_fixed` | published swapped (verified symptom: x = -38.59, y = -69.42); stored corrected |
| `invalid` | missing, unreadable or outside both ways: **no point stored** |

Why not a Neuquén box: the registry covers every province.

## Physical wells (`sigla`)
- One row in `geo.wells` per `sigla`, grouping its `idpozo` records (85,858 vs
  78,592, **verified**; the cause of the difference is **not verified**).
- The well's location is the point of its **lowest idpozo with a valid point**.
  If two records of the same well are more than 100 m apart, it is counted in the
  report (`wells_with_points_far_apart`).
- Evidence for the open question "why several idpozo per sigla?": the report
  counts wells whose records name **different formations**
  (`wells_with_several_formations`) and, apart, wells with a record whose
  `formacion` is **empty** (`wells_with_a_record_missing_formacion`). An empty
  value means "the registry does not say": it is never treated as a different
  formation and never filled in.

## Loads
- Each load records the file name, its SHA-256 fingerprint and the full report in
  `geo.load_runs`. The same file is skipped unless forced.
- Upserts: loading again updates rows, never duplicates them. One transaction:
  all or nothing.
- Migrations and loads run as `ingest_svc`, which owns the tables (ADR-0012).
