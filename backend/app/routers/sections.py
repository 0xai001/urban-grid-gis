"""Sections (UHASTKI) — CRUD routes."""
from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/sections", tags=["sections"])


def _to_out(row: models.Section) -> schemas.SectionOut:
    return schemas.SectionOut(
        id=row.id,
        district=row.district,
        cable_length_m=row.cable_length_m,
        rated_power_kw=row.rated_power_kw,
        rated_current_a=row.rated_current_a,
        wire_type=row.wire_type,
        installed_on=row.installed_on,
        avg_consumption_kwh=row.avg_consumption_kwh,
        geometry=json.loads(row.geometry),
        created_at=row.created_at,
    )


@router.get("", response_model=List[schemas.SectionOut])
def list_sections(db: Session = Depends(get_db)):
    return [_to_out(s) for s in db.query(models.Section).order_by(models.Section.id).all()]


@router.get("/{section_id}", response_model=schemas.SectionOut)
def get_section(section_id: int, db: Session = Depends(get_db)):
    row = db.get(models.Section, section_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Section not found")
    return _to_out(row)


@router.post("", response_model=schemas.SectionOut, status_code=status.HTTP_201_CREATED)
def create_section(body: schemas.SectionCreate, db: Session = Depends(get_db)):
    if body.id and db.get(models.Section, body.id):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Section {body.id} already exists")
    row = models.Section(
        id=body.id,
        district=body.district,
        cable_length_m=body.cable_length_m,
        rated_power_kw=body.rated_power_kw,
        rated_current_a=body.rated_current_a,
        wire_type=body.wire_type,
        installed_on=body.installed_on,
        avg_consumption_kwh=body.avg_consumption_kwh,
        geometry=json.dumps(body.geometry),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.patch("/{section_id}", response_model=schemas.SectionOut)
def update_section(section_id: int, body: schemas.SectionUpdate, db: Session = Depends(get_db)):
    row = db.get(models.Section, section_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Section not found")
    data = body.model_dump(exclude_unset=True)
    if "geometry" in data and data["geometry"] is not None:
        data["geometry"] = json.dumps(data["geometry"])
    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_section(section_id: int, db: Session = Depends(get_db)):
    row = db.get(models.Section, section_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Section not found")
    db.delete(row)
    db.commit()
    return None


@router.get("/{section_id}/readings", response_model=List[schemas.ReadingOut])
def list_section_readings(section_id: int, db: Session = Depends(get_db)):
    if not db.get(models.Section, section_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Section not found")
    rows = (
        db.query(models.Reading)
        .filter(models.Reading.section_id == section_id)
        .order_by(models.Reading.measured_on)
        .all()
    )
    return [schemas.ReadingOut.model_validate(r) for r in rows]
