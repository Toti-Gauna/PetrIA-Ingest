"""Read and clean the well registry ("Capítulo IV - Pozos").

Verified facts (docs/data-sources.md in the PetrIA repo): 26 columns, one row per
idpozo (85,858), 78,592 distinct sigla, the point is in `geojson` (longitude first).

Rules (docs/cleaning-rules.md):
- Every value is read as text, exactly as published. Only an EMPTY cell becomes
  "no value" (NULL); a literal text such as "NA" stays "NA".
- No unit conversion and no invented values. Problems are counted in the report.
- A row without sigla, or with an idpozo that is not a whole number, is rejected
  and its line number reported.
- The point is checked and, if published swapped, fixed and flagged (geo_points).
- Records are grouped into physical wells (sigla) with the owner's hash map.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import well_index
from .geo_points import INVALID, fix_point

EXPECTED_COLUMNS = [
    "sigla", "idpozo", "area", "cod_area", "empresa", "yacimiento", "cod_yacimiento",
    "formacion", "cuenca", "provincia", "cota", "profundidad", "clasificacion",
    "subclasificacion", "tipo_recurso", "sub_tipo_recurso", "gasplus", "tipopozo",
    "tipoextraccion", "tipoestado", "adjiv_fecha_inicio_perf", "adjiv_fecha_fin_perf",
    "adjiv_fecha_inicio_term", "adjiv_fecha_fin_term", "geojson", "geom",
]  # fmt: skip

# Descriptive columns kept as published text in geo.well_records.
# (sigla and idpozo are keys; geojson/geom become a checked PostGIS point.)
TEXT_COLUMNS = [c for c in EXPECTED_COLUMNS if c not in ("sigla", "idpozo", "geojson", "geom")]

# Two records of the same well whose points are farther apart than this are reported.
FAR_APART_METERS = 100.0
SAMPLE_SIZE = 10
_WHOLE_NUMBER = re.compile(r"^\d+$")


@dataclass
class CleanRegistry:
    wells: list[dict]  # one per sigla
    records: list[dict]  # one per idpozo
    report: dict  # every count, for the quality report


# --- reading -----------------------------------------------------------------


def detect_encoding(path: str | Path) -> str:
    """UTF-8 (with or without a BOM) if the bytes allow it, otherwise Latin-1."""
    raw = Path(path).read_bytes()
    try:
        raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return "latin-1"
    return "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"


def detect_delimiter(path: str | Path, encoding: str) -> str:
    """The separator used in the header line: comma, semicolon or tab."""
    with open(path, encoding=encoding) as f:
        header = f.readline()
    counts = {d: header.count(d) for d in (",", ";", "\t")}
    best = max(counts, key=counts.get)
    if counts[best] == 0:
        raise ValueError("Could not find a column separator in the header line.")
    return best


def read_registry(path: str | Path) -> tuple[pd.DataFrame, dict]:
    """Read the CSV as text. Stops with a clear error if an expected column is missing."""
    encoding = detect_encoding(path)
    delimiter = detect_delimiter(path, encoding)
    df = pd.read_csv(
        path,
        sep=delimiter,
        encoding=encoding,
        dtype=str,  # read everything as text: change nothing
        keep_default_na=False,  # do NOT treat "NA", "null", "N/A"... as missing
        na_values=[""],  # only an empty cell is missing
    )
    df.columns = [c.strip() for c in df.columns]
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"The file is missing expected columns {missing}. Stopping: never guess.")
    meta = {
        "encoding": encoding,
        "delimiter": {",": "comma", ";": "semicolon", "\t": "tab"}[delimiter],
        "extra_columns": [c for c in df.columns if c not in EXPECTED_COLUMNS],
    }
    return df, meta


# --- cleaning ----------------------------------------------------------------


def point_from_geojson(text: str | None) -> tuple[float | None, float | None, str | None]:
    """(longitude, latitude, problem). problem is None, 'missing' or 'unreadable'."""
    if text is None:
        return None, None, "missing"
    try:
        data = json.loads(text)
        coords = data["coordinates"]  # GeoJSON keeps the position under this key
        if data.get("type") != "Point" or len(coords) < 2:
            return None, None, "unreadable"
        lon, lat = float(coords[0]), float(coords[1])  # longitude first (verified)
    except (ValueError, TypeError, KeyError, AttributeError):
        return None, None, "unreadable"
    if not (math.isfinite(lon) and math.isfinite(lat)):
        return None, None, "unreadable"
    return lon, lat, None


def parse_idpozo(value: str | None) -> int | None:
    """A whole number, or None (the row is then rejected and reported)."""
    if value is None:
        return None
    value = value.strip()
    return int(value) if _WHOLE_NUMBER.match(value) else None


def approx_distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Approximate distance in meters (good enough to flag points far apart)."""
    meters_per_degree = 111_320.0
    x = (lon2 - lon1) * meters_per_degree * math.cos(math.radians((lat1 + lat2) / 2))
    y = (lat2 - lat1) * meters_per_degree
    return math.hypot(x, y)


def clean_registry(df: pd.DataFrame) -> CleanRegistry:
    # pandas "missing" -> Python None, row by row as plain dicts
    rows = df.astype(object).where(df.notna(), None).to_dict("records")

    rejected: dict[str, list[int]] = {"empty_sigla": [], "bad_idpozo": []}
    geojson_problems: Counter[str] = Counter()
    trimmed = duplicates = 0
    by_idpozo: dict[int, dict] = {}
    # Every (idpozo, sigla) pair, repeats included, so the hash map can catch a
    # record published under two different wells.
    pairs: list[tuple[int, str]] = []

    for i, row in enumerate(rows):
        line = i + 2  # line number in the file (line 1 is the header)
        raw_sigla = row["sigla"]
        sigla = raw_sigla.strip() if raw_sigla is not None else None
        if raw_sigla is not None and sigla != raw_sigla:
            trimmed += 1
        if not sigla:
            rejected["empty_sigla"].append(line)
            continue
        idpozo = parse_idpozo(row["idpozo"])
        if idpozo is None:
            rejected["bad_idpozo"].append(line)
            continue
        pairs.append((idpozo, sigla))
        if idpozo in by_idpozo:
            duplicates += 1  # keep the first; the hash map still checks the sigla
            continue
        lon, lat, problem = point_from_geojson(row["geojson"])
        if problem:
            geojson_problems[problem] += 1
        lon, lat, flag = fix_point(lon, lat)
        record = {"idpozo": idpozo, "sigla": sigla, **{c: row[c] for c in TEXT_COLUMNS}}
        record.update(lon=lon, lat=lat, location_flag=flag)
        by_idpozo[idpozo] = record

    # The owner's hash map: sigla -> sorted idpozo list. Raises ValueError if one
    # idpozo appears under two different sigla (we stop: never guess which is right).
    index = well_index.build_well_index(pairs)

    wells, far_apart = [], []
    several_formations, formation_missing = [], []
    for sigla, idpozos in index.items():
        recs = [by_idpozo[i] for i in idpozos]
        if len(recs) > 1:
            # Evidence for the open question "why several idpozo per sigla?" (ADR-0009).
            # An empty formacion means "the registry does not say": it is counted apart,
            # never treated as a different formation and never filled in.
            names = {r["formacion"] for r in recs if r["formacion"] is not None}
            if len(names) > 1:
                several_formations.append(sigla)
            if any(r["formacion"] is None for r in recs):
                formation_missing.append(sigla)
        located = [r for r in recs if r["location_flag"] != INVALID]
        chosen = located[0] if located else None  # lowest idpozo with a valid point
        if chosen and len(located) > 1:
            spread = max(
                approx_distance_m(chosen["lon"], chosen["lat"], r["lon"], r["lat"])
                for r in located[1:]
            )
            if spread > FAR_APART_METERS:
                far_apart.append(sigla)
        wells.append(
            {
                "sigla": sigla,
                "lon": chosen["lon"] if chosen else None,
                "lat": chosen["lat"] if chosen else None,
                "location_flag": chosen["location_flag"] if chosen else INVALID,
                "n_records": len(idpozos),
            }
        )

    records = list(by_idpozo.values())
    report = {
        "rows_read": len(rows),
        "rows_rejected": {k: len(v) for k, v in rejected.items()},
        "rejected_lines_sample": {k: v[:SAMPLE_SIZE] for k, v in rejected.items()},
        "duplicate_idpozo_rows": duplicates,
        "sigla_whitespace_trimmed": trimmed,
        "records": len(records),
        "wells": len(wells),
        "wells_with_several_records": sum(1 for w in wells if w["n_records"] > 1),
        "wells_with_several_formations": len(several_formations),
        "wells_with_several_formations_sample": several_formations[:SAMPLE_SIZE],
        "wells_with_a_record_missing_formacion": len(formation_missing),
        "wells_with_a_record_missing_formacion_sample": formation_missing[:SAMPLE_SIZE],
        "record_location_flags": dict(Counter(r["location_flag"] for r in records)),
        "well_location_flags": dict(Counter(w["location_flag"] for w in wells)),
        "geojson_problems": dict(geojson_problems),
        "wells_with_points_far_apart": len(far_apart),
        "wells_with_points_far_apart_sample": far_apart[:SAMPLE_SIZE],
        "records_formacion_vaca_muerta": sum(1 for r in records if r["formacion"] == "vaca muerta"),
        "records_by_provincia": dict(Counter(r["provincia"] for r in records).most_common()),
    }
    return CleanRegistry(wells=wells, records=records, report=report)
