# Urban Grid GIS

> A modern, web-based reimplementation of a 2006 university master's graduate project — a
> geographic information system for predictive maintenance of a city's
> electrical network. Same domain model, same algorithms, modern stack, plus a
> natural-language query endpoint.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)]()
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9-199900)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Why this exists

In 2006, this project was originally built in AutoCAD 2002 with AutoLISP, an
MS Access database, and an ODBC bridge — the standard GIS toolchain at the
time. It was defended at the [Taganrog State University of Radio
Engineering](https://en.wikipedia.org/wiki/Southern_Federal_University) (now
part of Southern Federal University).

Twenty years later, the same problem looks completely different. A modern web
GIS is a few hundred lines of Python and JavaScript, runs in any browser,
deploys for free, and can be queried in plain English. This repo is the 2026
version: identical feature set, identical core algorithm (least-squares
regression), but built so anyone with a browser can use it and anyone with a
GitHub account can deploy a copy.

If you're a hiring manager: the [Project history](docs/HISTORY.md) explains
the original 2006 architecture and what was modernized. The
[Architecture notes](docs/ARCHITECTURE.md) walk through the code top-to-bottom.

---

## What it does

A city's electrical grid is a collection of line segments (cables, overhead
lines), each with physical attributes (length, wire type, year installed) and
a stream of inspection readings over time (sag, resistance, axis deviation,
etc.). This system lets a maintenance planner:

1. **Browse the network on a map** — every segment is a clickable line.
2. **Manage segments and readings** — full CRUD via REST API or the UI.
3. **Run specialized analytics** — six built-in reports inherited from the
   2006 system (densest district, top consumption, aging segments, etc.).
4. **Forecast a parameter** — given a segment's reading history, fit a
   least-squares line and predict either:
   - what the value will be on a given date, or
   - the date on which it will reach a given threshold.
   This is the feature that lets you schedule repairs *before* something fails.
5. **Ask in plain English** — the AI query endpoint translates natural language
   into a safe filter spec and highlights the matching segments on the map.

---

## Tech stack

| Layer       | Choice                                      | Why                                                                |
| ----------- | ------------------------------------------- | ------------------------------------------------------------------ |
| Backend     | Python 3.11 + FastAPI                       | Tiny code, automatic OpenAPI docs, excellent type-checking         |
| ORM / DB    | SQLAlchemy 2 + SQLite                       | Zero-install. Drop-in upgrade to PostgreSQL/PostGIS later          |
| Forecasting | NumPy `polyfit`                             | Same least-squares algorithm as the 2006 thesis, in three lines    |
| Frontend    | Vanilla JS + Leaflet                        | No build step. Anyone can read the source and learn from it        |
| AI          | OpenAI-compatible chat API + JSON schema    | Model emits filters, never SQL — safe by construction              |
| Deploy      | Render free tier (one service, one URL)     | Zero-config, auto-deploys on every push                            |

---

## Run it locally (60 seconds)

You need Python 3.11+ and `git`.

```bash
git clone https://github.com/0xai001/urban-grid-gis.git
cd urban-grid-gis/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open <http://127.0.0.1:8000/> — the map and sidebar appear. The OpenAPI
docs are at <http://127.0.0.1:8000/docs>.

The first run auto-creates an SQLite database (`urban_grid.db`) and seeds it
with sample data taken straight from the 2006 thesis figures, geolocated over
Taganrog.

### Optional: enable the LLM-powered AI query

The natural-language endpoint works **out of the box** with a built-in
rule-based parser (no API key needed). To get smarter parsing, add an
OpenAI-compatible API key:

```bash
export OPENAI_API_KEY=sk-...
# Optional overrides:
export OPENAI_MODEL=gpt-4o-mini
export OPENAI_BASE_URL=https://api.openai.com/v1
```

Any OpenAI-compatible endpoint works (OpenAI, OpenRouter, Together, Groq,
local llama.cpp/Ollama with the right base URL).

---

## Deploy a live demo (free)

The repo ships with [`render.yaml`](deploy/render.yaml) for one-click deploys
on [Render](https://render.com). Push to GitHub, click "New → Blueprint" in
Render, point it at your fork, done. Set `OPENAI_API_KEY` as an environment
variable in the Render dashboard if you want the LLM path.

---

## Project layout

```
urban-grid-gis/
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py            # FastAPI app + frontend mount
│       ├── db.py              # SQLAlchemy engine/session
│       ├── models.py          # Section + Reading ORM models
│       ├── schemas.py         # Pydantic request/response shapes
│       ├── seed.py            # Sample data from the 2006 thesis
│       └── routers/
│           ├── sections.py    # CRUD on grid sections
│           ├── readings.py    # CRUD on time-series readings
│           ├── analytics.py   # Six specialized reports
│           ├── forecast.py    # Least-squares prediction
│           └── ai.py          # Plain-English query endpoint
├── frontend/
│   ├── index.html             # Single-page Leaflet UI
│   ├── style.css
│   └── app.js
├── docs/
│   ├── HISTORY.md             # 2006 origin story + what was modernized
│   └── ARCHITECTURE.md        # Code walkthrough
├── deploy/
│   └── render.yaml            # One-click free deploy on Render
├── scripts/
│   └── reset_db.py            # Wipe and re-seed the SQLite DB
├── LICENSE
└── README.md
```

---

## Roadmap (what I'd add next)

- PostGIS swap-in: replace the GeoJSON-in-text geometry column with a real
  spatial column and unlock proper spatial queries (`ST_Intersects`,
  `ST_DWithin`, etc.).
- Charting per section: time-series chart of every reading parameter, with the
  forecast line overlayed.
- Auth + multi-city: turn the demo into a small SaaS shell.
- ML upgrade to the forecaster: replace the simple line fit with a per-segment
  ARIMA/Prophet model and compare quality on the same UI.
- Repair-planning agent: an agent that reads the forecasts, prioritizes
  segments, and produces a draft maintenance schedule with reasoning.

---

## License

[MIT](LICENSE)
