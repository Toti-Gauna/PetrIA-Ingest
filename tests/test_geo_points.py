from petria_ingest.geo_points import fix_point, in_argentina


def test_good_point_stays_ok():
    assert fix_point(-69.4, -38.6) == (-69.4, -38.6, "ok")


def test_swapped_point_is_fixed_and_flagged():
    # The verified symptom: x = -38.59, y = -69.42.
    assert fix_point(-38.59, -69.42) == (-69.42, -38.59, "swapped_fixed")


def test_point_that_fits_neither_way_is_invalid_and_has_no_point():
    assert fix_point(0.0, 0.0) == (None, None, "invalid")


def test_missing_number_is_invalid():
    assert fix_point(None, -38.0) == (None, None, "invalid")
    assert fix_point(-69.0, None) == (None, None, "invalid")


def test_santa_cruz_point_is_not_touched():
    # The "Neuquén-only box" trap: a valid point far from Neuquén.
    assert fix_point(-69.2, -51.6) == (-69.2, -51.6, "ok")


def test_corner_where_both_orders_fit_is_kept_as_published():
    # Both numbers between -56 and -53: both orders fit, so we keep it as it came.
    assert in_argentina(-54.5, -55.0) and in_argentina(-55.0, -54.5)
    assert fix_point(-54.5, -55.0) == (-54.5, -55.0, "ok")


def test_box_edges_are_inside():
    assert in_argentina(-74.0, -56.0)
    assert in_argentina(-53.0, -21.5)
    assert not in_argentina(-52.9, -30.0)
