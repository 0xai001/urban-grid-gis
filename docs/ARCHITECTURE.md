# Architecture notes

A 10-minute tour of the codebase. If you're a hiring manager skimming this for
signal: every file is small enough to read in one screen.

## Big picture

```
Browser (Leaflet + vanilla JS)
         │
         │  HTTP (JSON)
         ▼
FastAPI (one process)
   ├── /api/sections        CRUD on grid segments
   ├── /api/readings        CRUD on time-series measurements
   ├── /api/analytics       Six specialized reports
   ├── /api/forecast        Least-squares prediction
   └── /api/ai/query        Plain-English → safe filter spec
         │
         │  SQLAlchemy
         ▼
SQLite (single file: urban_grid.db)
```

The same FastAPI process also serves the static frontend, so there is exactly
one thing to deploy.

## Data model

Two tables, one foreign-key relationship. The names of fields preserve the
original 2006 abbreviations as comments — easier to map back to the thesis.

```
sections (id PK)                 readings (pk PK)
├── district                     ├── section_id  FK → sections.id
├── cable_length_m               ├── measured_on
├── rated_power_kw               ├── coating_condition
├── rated_current_a              ├── sag_cm
├── wire_type                    ├── axis_deviation_cm
├── installed_on                 ├── vegetation_clearance_cm
├── avg_consumption_kwh          └── resistance_ohm
├── geometry  (GeoJSON LineString)
└── created_at
```

`geometry` is stored as a JSON string (a GeoJSON `LineString`). That keeps the
demo single-file. To upgrade to real spatial queries, swap SQLite for
PostgreSQL+PostGIS and change the column to a `Geometry('LINESTRING', 4326)` —
the rest of the code is unaffected.

## Forecasting (the interesting bit)

Each segment has a list of readings over time. For a chosen parameter (e.g.
`resistance_ohm`), we use NumPy `polyfit` to compute the line of best fit:

```python
slope, intercept = np.polyfit(days_since_first_reading, values, 1)
```

That's the entire forecasting model. From there:

- *Predict value on date:* `value = slope * days + intercept`
- *Predict date for value:* `days = (target - intercept) / slope`

This is identical to what the 2006 thesis described — the difference is that
back then it was implemented from scratch in AutoLISP; in 2026 it's a single
NumPy call.

## AI query: making it safe

The classic mistake in "ask your data" features is letting the model emit raw
SQL. We don't. The model is asked to output a small JSON document:

```json
{
  "section_filters": [{ "field": "installed_on", "op": "<", "value": "1985-01-01" }],
  "reading_filters": [{ "field": "sag_cm", "op": ">", "value": 25 }],
  "interpretation": "Cables installed before 1985 with current sag over 25 cm."
}
```

The backend then *interprets* that document by hand, with a hard-coded
whitelist of fields and operators. Any field the model invents is silently
ignored. Any operator that isn't in the small allowed set is silently
ignored. The result is that the worst the LLM can do is return zero rows —
it can't read or write anything outside the schema.

If no LLM is configured, a regex-based parser handles the most common
phrasings (`older than N years`, `sag over X`, `North district`, etc.). The
demo therefore works with or without an API key.

## What's deliberately *not* here

- **Auth.** This is a public demo; everything is read-write. Adding token
  auth is one FastAPI dependency.
- **A build step.** The frontend is plain HTML + JS so anyone reading the
  repo can understand it without learning a bundler.
- **A test suite.** A small `pytest` suite would be a nice next step; for the
  v1 demo, the API is small enough that the auto-generated `/docs` page lets
  you exercise every endpoint by hand in 60 seconds.

## Files worth reading first

If you only have time to look at a few files:

1. `backend/app/models.py` — the whole data model (~30 lines).
2. `backend/app/routers/forecast.py` — the predictive-maintenance algorithm.
3. `backend/app/routers/ai.py` — the safe NL-to-filter pattern.
4. `frontend/app.js` — how the map talks to the API.
