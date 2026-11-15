"""Administrative scope: Kharkiv Oblast (UA-63), pinned geoBoundaries geometry."""

import json
from functools import lru_cache
from pathlib import Path

PILOT_LATITUDE = 49.9935
PILOT_LONGITUDE = 36.2304
REGION_NAME = "Kharkiv Oblast"


@lru_cache(maxsize=1)
def boundary():
    return json.loads((Path(__file__).parent / "resources" / "kharkiv.geojson").read_text(encoding="utf-8"))


def polygons():
    geometry = boundary()["geometry"]
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"]
    raise ValueError("Unsupported administrative geometry")


@lru_cache(maxsize=1)
def bounds():
    points = [p for polygon in polygons() for ring in polygon for p in ring]
    return min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)


def ring_location(x, y, ring):
    """Return 0 outside, 1 inside, 2 on an edge; coordinate order is longitude/latitude."""
    inside = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        ax, ay = a[:2]
        bx, by = b[:2]
        cross = (x-ax)*(by-ay) - (y-ay)*(bx-ax)
        if abs(cross) <= 1e-12 and min(ax, bx)-1e-12 <= x <= max(ax, bx)+1e-12 and min(ay, by)-1e-12 <= y <= max(ay, by)+1e-12:
            return 2
        if (ay > y) != (by > y) and x < ax + (y-ay)*(bx-ax)/(by-ay):
            inside = not inside
    return int(inside)


def contains(latitude, longitude):
    west, south, east, north = bounds()
    if not west <= longitude <= east or not south <= latitude <= north:
        return False
    for polygon in polygons():
        outer = ring_location(longitude, latitude, polygon[0])
        if outer == 2:
            return True
        if outer and not any(ring_location(longitude, latitude, ring) for ring in polygon[1:]):
            return True
    return False


def require_region(latitude, longitude):
    if not contains(latitude, longitude):
        raise ValueError("Only Kharkiv Oblast (UA-63) is supported; point is outside its administrative boundary")
