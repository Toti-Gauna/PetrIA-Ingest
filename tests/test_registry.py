import csv
import json
from pathlib import Path

import pandas as pd
import pytest

from petria_ingest.registry import (
    EXPECTED_COLUMNS,
    clean_registry,
    point_from_geojson,
    read_registry,
)

FIXTURE = Path(__file__).parent / "fixtures" / "registry_synthetic.csv"


def _rewrite(src: Path, dst: Path, *, delimiter=",", encoding="utf-8", drop=None):
    with open(src, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    fields = [c for c in EXPECTED_COLUMNS if c != drop]
    with open(dst, "w", encoding=encoding, newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=delimiter, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return dst


# --- reading ---------------------------------------------------------------


def test_only_empty_cells_become_missing_and_na_text_stays():
    df, meta = read_registry(FIXTURE)
    assert len(df) == 9
    assert meta["encoding"] == "utf-8" and meta["delimiter"] == "comma"
    row_601 = df[df.idpozo == "601"].iloc[0]
    assert row_601.formacion == "NA"  # a literal text, not "missing"
    assert pd.isna(df[df.idpozo == "101"].iloc[0].area)  # empty cell -> missing


def test_values_are_read_as_text():
    df, _ = read_registry(FIXTURE)
    assert df.idpozo.tolist()[0] == "101"  # text, not the number 101


def test_missing_expected_column_stops_with_a_clear_error(tmp_path):
    bad = _rewrite(FIXTURE, tmp_path / "no_geojson.csv", drop="geojson")
    with pytest.raises(ValueError, match="geojson"):
        read_registry(bad)


def test_semicolon_separated_file_is_detected(tmp_path):
    semi = _rewrite(FIXTURE, tmp_path / "semi.csv", delimiter=";")
    df, meta = read_registry(semi)
    assert meta["delimiter"] == "semicolon" and len(df) == 9


def test_latin1_file_is_read_and_reported(tmp_path):
    latin = _rewrite(FIXTURE, tmp_path / "latin.csv", encoding="latin-1")
    df, meta = read_registry(latin)
    assert meta["encoding"] == "latin-1"
    assert "Neuquén" in df.provincia.tolist()


def test_point_from_geojson():
    good = json.dumps({"type": "Point", "coordinates": [-69.4, -38.6]})
    assert point_from_geojson(good) == (-69.4, -38.6, None)
    assert point_from_geojson(None) == (None, None, "missing")
    assert point_from_geojson("{not json") == (None, None, "unreadable")
    line = json.dumps({"type": "LineString", "coordinates": [[1, 2], [3, 4]]})
    assert point_from_geojson(line) == (None, None, "unreadable")


# --- cleaning (uses the owner's hash map) ----------------------------------


def _clean():
    df, _ = read_registry(FIXTURE)
    return clean_registry(df)


def test_report_counts_every_case():
    r = _clean().report
    assert r["rows_read"] == 9
    assert r["rows_rejected"] == {"empty_sigla": 1, "bad_idpozo": 1}
    assert r["rejected_lines_sample"] == {"empty_sigla": [7], "bad_idpozo": [8]}
    assert r["records"] == 7 and r["wells"] == 6
    assert r["wells_with_several_records"] == 1
    assert r["wells_with_several_formations"] == 0  # SYN-A-1: both "vaca muerta"
    assert r["record_location_flags"] == {"ok": 3, "swapped_fixed": 1, "invalid": 3}
    assert r["well_location_flags"] == {"ok": 2, "swapped_fixed": 1, "invalid": 3}
    assert r["geojson_problems"] == {"missing": 1, "unreadable": 1}
    assert r["sigla_whitespace_trimmed"] == 1
    assert r["records_formacion_vaca_muerta"] == 5


def test_two_records_make_one_well():
    clean = _clean()
    wells = {w["sigla"]: w for w in clean.wells}
    assert wells["SYN-A-1"]["n_records"] == 2


def test_swapped_point_is_stored_corrected():
    wells = {w["sigla"]: w for w in _clean().wells}
    b = wells["SYN-B-2"]
    assert (b["lon"], b["lat"], b["location_flag"]) == (-69.42, -38.59, "swapped_fixed")


def test_no_location_is_invented():
    wells = {w["sigla"]: w for w in _clean().wells}
    for sigla in ("SYN-D-4", "SYN-F-6", "SYN-G-7"):
        assert wells[sigla]["lon"] is None and wells[sigla]["location_flag"] == "invalid"


def test_sigla_spaces_are_trimmed():
    assert "SYN-F-6" in {w["sigla"] for w in _clean().wells}


def _df(rows):
    base = {c: None for c in EXPECTED_COLUMNS}
    return pd.DataFrame([{**base, **r} for r in rows], dtype=object)


def test_points_far_apart_in_the_same_well_are_reported():
    gj = lambda lon, lat: json.dumps({"type": "Point", "coordinates": [lon, lat]})  # noqa: E731
    df = _df(
        [
            {"sigla": "W", "idpozo": "1", "geojson": gj(-69.0, -38.0)},
            {"sigla": "W", "idpozo": "2", "geojson": gj(-69.5, -38.0)},  # ~44 km away
        ]
    )
    r = clean_registry(df).report
    assert r["wells_with_points_far_apart"] == 1
    assert r["wells_with_points_far_apart_sample"] == ["W"]


def test_formations_of_a_well_records_are_compared_and_empty_is_unknown():
    df = _df(
        [
            {"sigla": "SAME", "idpozo": "1", "formacion": "vaca muerta"},
            {"sigla": "SAME", "idpozo": "2", "formacion": "vaca muerta"},
            {"sigla": "MIXED", "idpozo": "3", "formacion": "vaca muerta"},
            {"sigla": "MIXED", "idpozo": "4", "formacion": "quintuco"},
            {"sigla": "UNKNOWN", "idpozo": "5", "formacion": "vaca muerta"},
            {"sigla": "UNKNOWN", "idpozo": "6", "formacion": None},  # the registry does not say
            {"sigla": "ALONE", "idpozo": "7", "formacion": None},  # one record: nothing to compare
        ]
    )
    r = clean_registry(df).report
    assert r["wells_with_several_formations"] == 1
    assert r["wells_with_several_formations_sample"] == ["MIXED"]
    assert r["wells_with_a_record_missing_formacion"] == 1  # an empty value is not "different"
    assert r["wells_with_a_record_missing_formacion_sample"] == ["UNKNOWN"]


def test_one_idpozo_under_two_wells_stops_the_cleaning():
    df = _df([{"sigla": "A", "idpozo": "1"}, {"sigla": "B", "idpozo": "1"}])
    with pytest.raises(ValueError):
        clean_registry(df)
