# Project history

## The 2006 original

The original system was the author's master's graduate project at the **Taganrog State
University of Radio Engineering** (TRTU), Faculty of Electronics and
Instrumentation, Department of Automated Scientific Research Systems and
Electronics (ASNIiE), defended in 2006. The thesis title
translates as:

> *Specialized geographic information system for planning repair work on a
> city's electrical networks.*

### Architecture, vintage 2006

| Layer | Original choice |
| --- | --- |
| Platform | AutoCAD 2002 (CAD package used as a drawing host) |
| Graphic database | A collection of `.dwg` (AutoCAD drawing) files |
| Semantic database | A single `.mdb` (Microsoft Access) file |
| DB driver | ODBC + ASI (AutoCAD SQL Interface) |
| Query language | SQL |
| Programming language | AutoLISP (a dialect of Lisp built into AutoCAD) |
| UI | AutoCAD menus + DCL dialog boxes |

Two normalized tables held all the semantic data:

- `UHASTKI` (sections of the line) — physical attributes of each segment.
- `POKAZANIY` (readings) — time-series inspection values per segment.

The two tables were linked by section ID, with the geometry side connected
through the same ID embedded in each AutoCAD primitive.

### Core feature: predictive maintenance

The unique idea was using **least-squares linear regression** on each segment's
historical readings to either:

1. predict what a parameter (sag, resistance, coating wear, …) will be on a
   future date, or
2. predict the date on which a parameter will cross a threshold.

That output drove the maintenance schedule — letting the planner act *before*
something failed.

---

## The 2026 modernization

| Concern | 2006 | 2026 |
| --- | --- | --- |
| Host environment | AutoCAD on a Windows PC | Any browser, any device |
| Geometry storage | `.dwg` files | GeoJSON in SQLite (or PostGIS) |
| Semantic storage | MS Access `.mdb` | SQLite via SQLAlchemy |
| API | AutoLISP procedures | REST + OpenAPI (`/docs`) |
| UI | AutoCAD windows + DCL dialogs | Leaflet + a JS sidebar |
| Querying | Hand-written SQL inside AutoLISP | REST endpoints + plain-English query |
| Forecasting | Custom Lisp implementation of least-squares | NumPy `polyfit` (same algorithm, three lines) |
| Deployment | "Install AutoCAD on every workstation" | One free Render service, anyone with a URL |

The **domain model** (two tables, one foreign-key relationship) and the
**core algorithm** (least-squares linear regression) are unchanged on
purpose. The point of this repo is to show what *modernizing* looks like:
keep the parts that were right, replace the parts that aged.

### What's new in 2026

- **Natural-language query.** A plain-English question is translated into a
  safe filter spec (a small JSON document, not free SQL) and executed
  against whitelisted columns. The matching segments are highlighted on the
  map.
- **OpenAPI docs.** Every endpoint is auto-documented and clickable at
  `/docs` — instant discoverability for anyone reviewing the project.
- **Free deploy.** Render's free tier hosts the whole thing as a single web
  service. Push to GitHub, get a public URL.

### Files preserved as artifacts (not in this repo)

The original 2006 source materials — the AutoLISP code, the `.dwg` drawings,
the `.mdb` database, the explanatory note, the title page, the speech, and the
posters — are kept on the author's local archive. The thesis itself is
referenced as historical context only; nothing from it is required to run this
modernized version.
