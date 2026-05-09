"""Specialized analytics — the six 'specific' GIS functions from the 2006 master's project.

Original function (translated) -> modern endpoint:

- "Find the city district with the largest number of grid sections"
    -> GET /api/analytics/densest-district
- "Find grid sections that need replacement based on installation year"
    -> GET /api/analytics/aging-sections?older_than_years=N
- "Find the city district with the highest electricity consumption"
    -> GET /api/analytics/highest-consumption-district
- "Find the grid section with the highest electricity consumption"
    -> GET /api/analytics/highest-consumption-section
- (forecasting lives in routers/forecast.py — those are the last two)
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/densest-district", response_model=schemas.DistrictCount)
def densest_district(db: Session = Depends(get_db)):
    """Which district has the highest number of grid sections?"""
    row = (
        db.query(models.Section.district, func.count(models.Section.id).label("n"))
        .group_by(models.Section.district)
        .order_by(func.count(models.Section.id).desc())
        .first()
    )
    if not row:
        return schemas.DistrictCount(district="", section_count=0)
    return schemas.DistrictCount(district=row[0] or "Unknown", section_count=row[1])


@router.get("/district-counts", response_model=List[schemas.DistrictCount])
def district_counts(db: Session = Depends(get_db)):
    """All districts ranked by section count (handy for charts)."""
    rows = (
        db.query(models.Section.district, func.count(models.Section.id).label("n"))
        .group_by(models.Section.district)
        .order_by(func.count(models.Section.id).desc())
        .all()
    )
    return [schemas.DistrictCount(district=r[0] or "Unknown", section_count=r[1]) for r in rows]


@router.get("/aging-sections", response_model=List[schemas.AgingSection])
def aging_sections(
    older_than_years: int = Query(30, ge=0, le=200, description="Min age threshold"),
    db: Session = Depends(get_db),
):
    """Sections older than N years — candidates for replacement."""
    now = datetime.utcnow()
    out: list[schemas.AgingSection] = []
    for s in db.query(models.Section).all():
        age = (now - s.installed_on).days / 365.25
        if age >= older_than_years:
            out.append(
                schemas.AgingSection(
                    id=s.id,
                    installed_on=s.installed_on,
                    age_years=round(age, 1),
                    wire_type=s.wire_type,
                )
            )
    out.sort(key=lambda x: x.age_years, reverse=True)
    return out


@router.get("/highest-consumption-district", response_model=schemas.DistrictCount)
def highest_consumption_district(db: Session = Depends(get_db)):
    """District with the highest sum of avg_consumption_kwh — returns count too."""
    row = (
        db.query(
            models.Section.district,
            func.sum(models.Section.avg_consumption_kwh).label("total"),
        )
        .group_by(models.Section.district)
        .order_by(func.sum(models.Section.avg_consumption_kwh).desc())
        .first()
    )
    if not row:
        return schemas.DistrictCount(district="", section_count=0)
    # Re-purpose section_count to mean total kWh for this endpoint, rounded.
    return schemas.DistrictCount(district=row[0] or "Unknown", section_count=int(row[1] or 0))


@router.get("/highest-consumption-section", response_model=schemas.ConsumptionRow)
def highest_consumption_section(db: Session = Depends(get_db)):
    """Single grid section with the highest avg consumption."""
    s = (
        db.query(models.Section)
        .order_by(models.Section.avg_consumption_kwh.desc())
        .first()
    )
    if not s:
        return schemas.ConsumptionRow(id=0, avg_consumption_kwh=0.0)
    return schemas.ConsumptionRow(
        id=s.id, district=s.district, avg_consumption_kwh=s.avg_consumption_kwh
    )


@router.get("/top-consumption-sections", response_model=List[schemas.ConsumptionRow])
def top_consumption_sections(
    limit: int = Query(5, ge=1, le=100), db: Session = Depends(get_db)
):
    """Top-N sections by avg consumption."""
    rows = (
        db.query(models.Section)
        .order_by(models.Section.avg_consumption_kwh.desc())
        .limit(limit)
        .all()
    )
    return [
        schemas.ConsumptionRow(
            id=s.id, district=s.district, avg_consumption_kwh=s.avg_consumption_kwh
        )
        for s in rows
    ]
