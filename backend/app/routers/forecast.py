"""Forecasting — the unique feature of the 2006 master's project.

The original used the *least-squares method* to fit a straight line to a section's
historical readings, then either (a) predicted the parameter value on a future
date or (b) predicted the date on which the parameter will reach a target value.
Repair planning is built on top of these two functions.

We faithfully reproduce that algorithm here, with numpy doing the linear algebra.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Tuple

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/forecast", tags=["forecast"])

ALLOWED_PARAMS = {
    "coating_condition",
    "sag_cm",
    "axis_deviation_cm",
    "vegetation_clearance_cm",
    "resistance_ohm",
}


def _fit_line(
    db: Session, section_id: int, parameter: str
) -> Tuple[float, float, int, datetime]:
    """Return (slope_per_day, intercept_at_first_reading, n, first_date) for
    a section's readings on the given parameter using ordinary least squares.

    Time axis is "days since the first reading" — keeps numbers small.
    """
    if parameter not in ALLOWED_PARAMS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown parameter: {parameter}")
    if not db.get(models.Section, section_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Section not found")

    rows = (
        db.query(models.Reading)
        .filter(models.Reading.section_id == section_id)
        .order_by(models.Reading.measured_on)
        .all()
    )
    if len(rows) < 2:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Need at least two readings to fit a forecast line",
        )

    first_date = rows[0].measured_on
    x = np.array(
        [(r.measured_on - first_date).total_seconds() / 86400.0 for r in rows], dtype=float
    )
    y = np.array([getattr(r, parameter) for r in rows], dtype=float)
    # numpy least-squares: y = slope * x + intercept
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope), float(intercept), len(rows), first_date


@router.post("/value-on-date", response_model=schemas.ForecastValueResponse)
def forecast_value_on_date(
    body: schemas.ForecastValueRequest, db: Session = Depends(get_db)
):
    """Predicts what the parameter value will be on a given date."""
    slope, intercept, n, first_date = _fit_line(db, body.section_id, body.parameter)
    days = (body.target_date - first_date).total_seconds() / 86400.0
    predicted = slope * days + intercept
    return schemas.ForecastValueResponse(
        section_id=body.section_id,
        parameter=body.parameter,
        target_date=body.target_date,
        predicted_value=round(predicted, 4),
        slope=slope,
        intercept=intercept,
        sample_count=n,
    )


@router.post("/date-for-value", response_model=schemas.ForecastDateResponse)
def forecast_date_for_value(
    body: schemas.ForecastDateRequest, db: Session = Depends(get_db)
):
    """Predicts the date on which the parameter will reach a target value."""
    slope, intercept, n, first_date = _fit_line(db, body.section_id, body.parameter)
    predicted_date: datetime | None = None
    if abs(slope) > 1e-12:  # avoid division by zero / flat trends
        days = (body.target_value - intercept) / slope
        # Sanity-cap so we don't produce silly dates 10,000 years out.
        if -36500 < days < 365 * 200:
            predicted_date = first_date + timedelta(days=days)
    return schemas.ForecastDateResponse(
        section_id=body.section_id,
        parameter=body.parameter,
        target_value=body.target_value,
        predicted_date=predicted_date,
        slope=slope,
        intercept=intercept,
        sample_count=n,
    )
