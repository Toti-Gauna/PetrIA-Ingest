"""Is a well's point plausible, and was it published with longitude and latitude swapped?

Verified symptom (docs/data-sources.md in the PetrIA repo): some points have
x = -38.59 and y = -69.42. Argentine longitudes never reach -38 and no latitude is
-69, so those two numbers were published in the wrong order.

Why an Argentina box and not a Neuquén one: the registry has wells from every
province (Mendoza, Rio Negro, Santa Cruz...). A Neuquén box would flag good wells.

The box is a setting: a generous rectangle around Argentina (mainland and Tierra
del Fuego), in degrees, WGS 84. Adding another country later means another box.
"""

LON_MIN, LON_MAX = -74.0, -53.0  # west, east
LAT_MIN, LAT_MAX = -56.0, -21.5  # south, north

OK = "ok"
SWAPPED_FIXED = "swapped_fixed"
INVALID = "invalid"


def in_argentina(lon: float, lat: float) -> bool:
    """True when the point falls inside the Argentina box."""
    return LON_MIN <= lon <= LON_MAX and LAT_MIN <= lat <= LAT_MAX


def fix_point(lon: float | None, lat: float | None) -> tuple[float | None, float | None, str]:
    """Return (longitude, latitude, flag).

    ok            the point was fine as published
    swapped_fixed it was published swapped; we return it in the right order
    invalid       it fits neither way (or a number is missing): no point, never invented

    Known corner: if both numbers lie between -56 and -53, both orders fit the box;
    the point is kept as published ("ok"). It is a tiny area and a test locks it.
    """
    if lon is None or lat is None:
        return None, None, INVALID
    if in_argentina(lon, lat):
        return lon, lat, OK
    if in_argentina(lat, lon):  # try them swapped
        return lat, lon, SWAPPED_FIXED
    return None, None, INVALID
