"""Natural-language query endpoint — the 2026 'agentic' twist.

You can ask plain-English questions like:

  "Show me cables installed before 1985 with sag over 25 cm"
  "Which sections in the North district consume more than 5000 kWh?"
  "List sections older than 30 years"

The endpoint:

1. If `OPENAI_API_KEY` is set in the environment, it asks an OpenAI-compatible
   chat model to extract a small JSON "filter spec" (whitelisted fields and
   operators only — never raw SQL).
2. If no API key is available, it falls back to a regex-based parser that
   handles common phrasings. The fallback is intentionally simple — it's
   enough so the demo works offline.
3. Either way, the filter spec is then translated into a SAFE SQLAlchemy query
   against the whitelisted columns, and the matching sections are returned.

This avoids the classic LLM-tool-use pitfall of letting the model run arbitrary
SQL. The model only emits filters; the backend executes them.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import and_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..db import get_db

router = APIRouter(prefix="/api/ai", tags=["ai"])

# Whitelisted filter targets — model can only filter on these.
SECTION_FIELDS = {
    "id": "int",
    "district": "str",
    "cable_length_m": "float",
    "rated_power_kw": "float",
    "rated_current_a": "float",
    "wire_type": "str",
    "installed_on": "datetime",
    "avg_consumption_kwh": "float",
}

READING_FIELDS = {
    "coating_condition": "float",
    "sag_cm": "float",
    "axis_deviation_cm": "float",
    "vegetation_clearance_cm": "float",
    "resistance_ohm": "float",
}

OPERATORS = {">", ">=", "<", "<=", "==", "!=", "contains"}

SYSTEM_PROMPT = f"""You translate user questions about an urban electrical grid GIS
into a JSON filter spec. Output ONLY JSON, no prose.

Schema:
- "section_filters": list of {{ "field": str, "op": str, "value": str|number }}
- "reading_filters": list of {{ "field": str, "op": str, "value": number }}
- "interpretation": short English restatement of what you understood.

Allowed section fields: {sorted(SECTION_FIELDS)}.
Allowed reading fields: {sorted(READING_FIELDS)} (these match LATEST reading per section).
Allowed ops: {sorted(OPERATORS)}.

Dates must be ISO-8601 strings (YYYY-MM-DD). Do not invent fields. If the
question can't be answered with the schema, return empty filter lists and
explain why in "interpretation".
"""


# ---------- LLM path -----------------------------------------------------

async def _llm_filter_spec(question: str) -> dict[str, Any] | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "temperature": 0,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception:
        return None


# ---------- Rule-based fallback -----------------------------------------

_NUM = r"[-+]?\d+(?:\.\d+)?"


def _rule_filter_spec(q: str) -> dict[str, Any]:
    """Tiny offline parser. Catches the most common phrasings used in the
    master's project example questions. Never raises — returns empty lists if it
    doesn't understand."""
    s = q.lower()
    section_filters: list[dict[str, Any]] = []
    reading_filters: list[dict[str, Any]] = []

    # "older than N years" / "installed before YYYY"
    m = re.search(r"older\s+than\s+(\d{1,3})\s*year", s)
    if m:
        years = int(m.group(1))
        cutoff = datetime.utcnow().replace(year=datetime.utcnow().year - years)
        section_filters.append({"field": "installed_on", "op": "<", "value": cutoff.date().isoformat()})
    m = re.search(r"(?:before|prior\s+to)\s+(\d{4})", s)
    if m:
        section_filters.append({"field": "installed_on", "op": "<", "value": f"{m.group(1)}-01-01"})
    m = re.search(r"after\s+(\d{4})", s)
    if m:
        section_filters.append({"field": "installed_on", "op": ">", "value": f"{m.group(1)}-12-31"})

    # district mentions
    for d in ["north", "south", "east", "west", "central", "centre", "center"]:
        if re.search(rf"\b{d}\b", s):
            label = d.replace("centre", "central").replace("center", "central").title()
            section_filters.append({"field": "district", "op": "contains", "value": label})
            break

    # consumption thresholds
    m = re.search(rf"consum\w*\s+(?:more|greater|higher|over|above)\s+(?:than\s+)?({_NUM})", s)
    if m:
        section_filters.append({"field": "avg_consumption_kwh", "op": ">", "value": float(m.group(1))})
    m = re.search(rf"consum\w*\s+(?:less|lower|under|below)\s+(?:than\s+)?({_NUM})", s)
    if m:
        section_filters.append({"field": "avg_consumption_kwh", "op": "<", "value": float(m.group(1))})

    # reading thresholds — sag, resistance, etc.
    reading_terms = {
        "sag": "sag_cm",
        "resistance": "resistance_ohm",
        "deviation": "axis_deviation_cm",
        "coating": "coating_condition",
        "vegetation": "vegetation_clearance_cm",
        "clearance": "vegetation_clearance_cm",
    }
    for term, field in reading_terms.items():
        m = re.search(rf"{term}\s+(?:over|above|greater\s+than|more\s+than|>)\s+({_NUM})", s)
        if m:
            reading_filters.append({"field": field, "op": ">", "value": float(m.group(1))})
        m = re.search(rf"{term}\s+(?:under|below|less\s+than|<)\s+({_NUM})", s)
        if m:
            reading_filters.append({"field": field, "op": "<", "value": float(m.group(1))})

    interp_bits = []
    if section_filters:
        interp_bits.append(f"section filters: {section_filters}")
    if reading_filters:
        interp_bits.append(f"reading filters: {reading_filters}")
    interpretation = "; ".join(interp_bits) or "No filters extracted; returning all sections."

    return {
        "section_filters": section_filters,
        "reading_filters": reading_filters,
        "interpretation": interpretation,
    }


# ---------- Filter execution -------------------------------------------

def _build_section_clause(field: str, op: str, value: Any):
    if field not in SECTION_FIELDS or op not in OPERATORS:
        return None
    col = getattr(models.Section, field)
    if SECTION_FIELDS[field] == "datetime" and isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    if op == ">":
        return col > value
    if op == ">=":
        return col >= value
    if op == "<":
        return col < value
    if op == "<=":
        return col <= value
    if op == "==":
        return col == value
    if op == "!=":
        return col != value
    if op == "contains":
        return col.ilike(f"%{value}%")
    return None


def _section_ids_matching_reading_filters(
    db: Session, reading_filters: list[dict[str, Any]]
) -> set[int] | None:
    """Returns the set of section IDs whose LATEST reading matches all filters.

    Returns None if no reading filters were given (means "don't restrict")."""
    if not reading_filters:
        return None
    candidate_ids: set[int] | None = None
    for f in reading_filters:
        field = f.get("field")
        op = f.get("op")
        value = f.get("value")
        if field not in READING_FIELDS or op not in OPERATORS:
            continue
        col = getattr(models.Reading, field)
        # Latest reading per section: subquery picks max measured_on per section.
        from sqlalchemy import func
        latest_dates = (
            db.query(
                models.Reading.section_id.label("sid"),
                func.max(models.Reading.measured_on).label("md"),
            )
            .group_by(models.Reading.section_id)
            .subquery()
        )
        q = (
            db.query(models.Reading.section_id)
            .join(
                latest_dates,
                and_(
                    models.Reading.section_id == latest_dates.c.sid,
                    models.Reading.measured_on == latest_dates.c.md,
                ),
            )
        )
        if op == ">":
            q = q.filter(col > value)
        elif op == ">=":
            q = q.filter(col >= value)
        elif op == "<":
            q = q.filter(col < value)
        elif op == "<=":
            q = q.filter(col <= value)
        elif op == "==":
            q = q.filter(col == value)
        elif op == "!=":
            q = q.filter(col != value)
        ids = {row[0] for row in q.all()}
        candidate_ids = ids if candidate_ids is None else candidate_ids & ids
    return candidate_ids or set()


@router.post("/query", response_model=schemas.AIQueryResponse)
async def ai_query(body: schemas.AIQueryRequest, db: Session = Depends(get_db)):
    spec = await _llm_filter_spec(body.question)
    if spec is None:
        spec = _rule_filter_spec(body.question)

    section_filters = spec.get("section_filters", []) or []
    reading_filters = spec.get("reading_filters", []) or []
    interpretation = spec.get("interpretation")

    # Build SQLAlchemy query for sections.
    q = db.query(models.Section)
    for f in section_filters:
        clause = _build_section_clause(f.get("field"), f.get("op"), f.get("value"))
        if clause is not None:
            q = q.filter(clause)

    # Constrain by reading filters (latest reading match), if any.
    rid_set = _section_ids_matching_reading_filters(db, reading_filters)
    if rid_set is not None:
        if not rid_set:
            ids: list[int] = []
        else:
            ids = [s.id for s in q.filter(models.Section.id.in_(rid_set)).all()]
    else:
        ids = [s.id for s in q.all()]

    if not ids:
        answer = "No sections matched your query."
    else:
        answer = f"Found {len(ids)} matching section(s): {', '.join(str(i) for i in ids[:25])}"
        if len(ids) > 25:
            answer += f" … and {len(ids) - 25} more."

    return schemas.AIQueryResponse(
        answer=answer,
        matched_section_ids=ids,
        interpretation=interpretation,
    )
