"""SQLAlchemy ORM models.

These map to the two tables from the 2006 master's project, modernized:

- `Section` (was `UHASTKI`): a segment of overhead/cable power line.
- `Reading` (was `POKAZANIY`): a time-series measurement on that segment.

Geometry is stored as GeoJSON LineString in a TEXT column. That's enough for the
demo and avoids requiring a PostGIS-enabled database. If you later swap SQLite
for PostgreSQL+PostGIS, change `geometry` to a `Geometry('LINESTRING', 4326)`
column from GeoAlchemy2 — the rest of the app keeps working.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .db import Base


class Section(Base):
    """A segment of urban electrical line (LEP) — was `UHASTKI` in the original."""

    __tablename__ = "sections"

    id = Column(Integer, primary_key=True)  # was: ID (numeric identifier)
    district = Column(String, nullable=True)  # city district

    # Physical / electrical attributes — names below map to the original fields:
    cable_length_m = Column(Float, nullable=False)        # LENKAB — cable length
    rated_power_kw = Column(Float, nullable=False)        # MOJNOST — rated power
    rated_current_a = Column(Float, nullable=False)       # FTOKA — current
    wire_type = Column(String, nullable=False)            # TIPPROV — wire type
    installed_on = Column(DateTime, nullable=False)       # TIMEZAKL — installation date
    avg_consumption_kwh = Column(Float, nullable=False)   # SRPOTR — average consumption

    # GeoJSON LineString as text (kept simple; PostGIS-ready later).
    geometry = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    readings = relationship(
        "Reading", back_populates="section", cascade="all, delete-orphan"
    )


class Reading(Base):
    """Time-series characteristic measurement — was `POKAZANIY` in the original."""

    __tablename__ = "readings"

    pk = Column(Integer, primary_key=True, autoincrement=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)

    measured_on = Column(DateTime, nullable=False)        # Datapr — measurement date
    coating_condition = Column(Float, nullable=False)     # Sostpokr — wire coating condition
    sag_cm = Column(Float, nullable=False)                # Proves — cable sag
    axis_deviation_cm = Column(Float, nullable=False)     # Otklon — deviation from axis
    vegetation_clearance_cm = Column(Float, nullable=False)  # Rastit — clearance to vegetation
    resistance_ohm = Column(Float, nullable=False)        # R — electrical resistance

    section = relationship("Section", back_populates="readings")
