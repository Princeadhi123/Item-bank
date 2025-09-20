# Item Bank Explorer

A beautiful, modern UI powered by FastAPI to explore your SQLite Item Bank. It loads and filters exactly the records from your database (e.g., the 464 rows in the `items` table) and shows detailed item information from related tables.

## Project Layout

- `data/items.db` — your SQLite database
- `main.py` — FastAPI backend exposing `/api` endpoints and serving the frontend
- `static/` — Frontend UI (HTML/CSS/JS)
  - `static/index.html`
  - `static/styles.css`
  - `static/app.js`
- `requirements.txt` — Python dependencies

## Features

- Search across `label`, `name`, `source`, and NuTa `contents`
- Filters for type, hierarchical level, content area (S1..S6), target areas (T10..T20), NuTa skill levels, and sources
- Numeric ranges for `meanp_all_classical` and `a_irt`
- Sorting by ID, label, type, level, meanp, a_irt
- Pagination with total count and page navigation
- Details drawer with content areas, difficulty, discrimination, NuTa breakdown, and targets
- Responsive layout with light/dark themes

## Prerequisites

- Python 3.9+ recommended
- `data/items.db` present (already in this project)

## Setup & Run

1. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. Run the server:

   ```powershell
   python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

3. Open the app in your browser:

   - [http://127.0.0.1:8000](http://127.0.0.1:8000)

## API Endpoints

- `GET /api/items` — list items with filters, sorting, and pagination
- `GET /api/items/{id}` — get the full detail for a single item
- `GET /api/filters` — get filter options (types, levels, sources, etc.)
- `GET /api/health` — check server health

## Notes

- The UI reads data only from your SQLite DB; no mock data. Total items shown equals the count found in `items`.
- If you previously edited a `styles.css` at the project root, note that the UI serves assets from `static/`. Move your styles into `static/styles.css` if needed.
