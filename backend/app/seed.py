"""Sample data — based on the example tables from the 2006 master's project.

The original `UHASTKI` and `POKAZANIY` figures (Fig. 3.1 and 3.2) gave a small
realistic dataset; we keep those values and place each section on a real
Taganrog street. All geometries below were picked by hand so that:

- every line segment lies on land (Taganrog sits on a peninsula in the Sea of
  Azov, so blind lon/lat offsets land in the water — we avoid that);
- each line follows a recognizable street, so the map looks like a real grid
  rather than scattered diagonal sticks;
- districts roughly match the city's actual neighborhoods.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Iterable, List, Tuple

from sqlalchemy.orm import Session

from . import models


# A GeoJSON LineString takes [lon, lat] pairs (note the order: x, y).
Coord = Tuple[float, float]


def _line(coords: List[Coord]) -> dict:
    return {"type": "LineString", "coordinates": [list(c) for c in coords]}


# Each section is anchored to a plausible street in Taganrog. The vertices
# below were chosen from the OpenStreetMap basemap so that the line visibly
# follows a road rather than cutting across blocks or sea.
SECTIONS_SEED = [
    # id, district, len_m, kw, A, wire_type, installed_iso, avg_kwh, coords
    (
        696019421, "North", 6666, 100, 50, "AC-95", "1989-12-12", 5412,
        # Northern arc through Sobacheevka along Aleksandrovskaya / Oktyabrskaya streets
        [(38.913, 47.227), (38.922, 47.226), (38.933, 47.226), (38.944, 47.225)],
    ),
    (
        784789676, "South", 800, 50, 30, "AC-50", "1981-02-12", 987,
        # Short branch on ulitsa Shevchenko, well north of the southern shore
        [(38.918, 47.211), (38.926, 47.211)],
    ),
    (
        785626805, "Central", 1200, 80, 20, "AC-70", "1996-05-12", 1100,
        # Aleksandrovskaya ulitsa in the city center
        [(38.926, 47.215), (38.934, 47.214), (38.942, 47.213)],
    ),
    (
        786300995, "North", 900, 80, 45, "AC-50", "1985-08-15", 999,
        # Smaller north-side feeder, around ulitsa Lenina
        [(38.928, 47.224), (38.934, 47.222)],
    ),
    (
        787011169, "East", 6547, 100, 50, "AC-120", "1999-12-12", 6211,
        # Long east-bound trunk along Petrovskaya / Portovaya toward the port,
        # stopping at the port edge so it stays inside the city
        [(38.935, 47.214), (38.942, 47.213), (38.948, 47.212)],
    ),
    (
        929326713, "West", 800, 25, 30, "AC-95", "1997-12-12", 1569,
        # West side, near ulitsa Svobody / Sportivnaya
        [(38.892, 47.214), (38.892, 47.220)],
    ),
    (
        746913692, "Central", 500, 60, 25, "AC-70", "1988-12-12", 2300,
        # Short feeder on ulitsa Chekhova, central part
        [(38.921, 47.218), (38.924, 47.215)],
    ),
    (
        745997350, "South", 1100, 90, 40, "AC-95", "1989-03-19", 3450,
        # South-side trunk along ulitsa Lomakina (kept just north of the shore)
        [(38.916, 47.213), (38.926, 47.212), (38.934, 47.212)],
    ),
]


# (section_id, date, coating, sag, deviation, vegetation_clearance, resistance)
READINGS_SEED = [
    (746913692, "1988-12-12", 4.5,  8, 10, 120, 10),
    (745997350, "1989-03-19", 4.2,  5,  9, 110, 12),
    (746913692, "1992-12-12", 3.9, 15, 19, 111, 32),
    (745997350, "1993-03-19", 3.5, 20, 22, 105, 16),
    (745997350, "1996-12-12", 3.5, 26, 30, 102, 40),
    (746913692, "1997-12-12", 2.9, 29, 30, 100, 25),
    # Extra readings on the bigger sections, so the forecaster has data to work with:
    (696019421, "2010-06-01", 4.8, 10, 12, 130, 14),
    (696019421, "2018-06-01", 4.0, 22, 20, 115, 28),
    (696019421, "2024-06-01", 3.4, 33, 28, 100, 42),
    (787011169, "2012-04-01", 4.9,  8,  9, 140,  9),
    (787011169, "2019-04-01", 4.4, 14, 13, 128, 18),
    (787011169, "2025-04-01", 4.0, 22, 18, 118, 26),
    (785626805, "2005-09-01", 4.7,  6,  8, 135, 11),
    (785626805, "2015-09-01", 4.1, 16, 14, 120, 22),
    (785626805, "2024-09-01", 3.6, 24, 22, 108, 33),
]


def seed_sample_data(db: Session) -> None:
    for sid, district, length, kw, amp, wtype, iso, kwh, coords in SECTIONS_SEED:
        db.add(
            models.Section(
                id=sid,
                district=district,
                cable_length_m=float(length),
                rated_power_kw=float(kw),
                rated_current_a=float(amp),
                wire_type=wtype,
                installed_on=datetime.fromisoformat(iso),
                avg_consumption_kwh=float(kwh),
                geometry=json.dumps(_line(coords)),
            )
        )
    db.flush()

    for sid, iso, coat, sag, dev, veg, r in READINGS_SEED:
        db.add(
            models.Reading(
                section_id=sid,
                measured_on=datetime.fromisoformat(iso),
                coating_condition=float(coat),
                sag_cm=float(sag),
                axis_deviation_cm=float(dev),
                vegetation_clearance_cm=float(veg),
                resistance_ohm=float(r),
            )
        )
    db.commit()
