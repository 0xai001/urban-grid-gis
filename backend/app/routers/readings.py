"""Readings (POKAZANIY) — CRUD routes."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/readings", tags=["readings"])


@router.get("", response_model=List[schemas.ReadingOut])
def list_readings(db: Session = Depends(get_db)):
    return [
        schemas.ReadingOut.model_validate(r)
        for r in db.query(models.Reading).order_by(models.Reading.measured_on).all()
    ]


@router.post("", response_model=schemas.ReadingOut, status_code=status.HTTP_201_CREATED)
def create_reading(body: schemas.ReadingCreate, db: Session = Depends(get_db)):
    if not db.get(models.Section, body.section_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Section not found")
    row = models.Reading(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return schemas.ReadingOut.model_validate(row)


@router.delete("/{pk}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reading(pk: int, db: Session = Depends(get_db)):
    row = db.get(models.Reading, pk)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reading not found")
    db.delete(row)
    db.commit()
    return None
