"""Tests for the owner's hash map (lesson 1.1, algorithm spot, mode: no-AI)."""

import pytest

from petria_ingest.well_index import build_well_index


def test_groups_records_under_their_well():
    assert build_well_index([(1, "A"), (2, "A"), (3, "B")]) == {"A": [1, 2], "B": [3]}


def test_empty_input_gives_empty_index():
    assert build_well_index([]) == {}


def test_one_record_under_two_wells_is_an_error():
    with pytest.raises(ValueError):
        build_well_index([(1, "A"), (1, "B")])


def test_identical_repeated_pair_is_counted_once():  # the bonus
    assert build_well_index([(1, "A"), (1, "A")]) == {"A": [1]}


def test_lists_come_out_sorted():
    assert build_well_index([(3, "A"), (1, "A"), (2, "A")]) == {"A": [1, 2, 3]}
