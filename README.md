# Item Bank Backend (FastAPI + SQLite)

This backend ingests Sheet 2 from your Excel file into an SQLite table named `items`, and provides endpoints to query it.

- Excel Path: `c:\\Users\\pdaadh\\Desktop\\Item bank\\Item bank from DigiArvi 2025 - Final.xlsx`
- Table: `items`
- Database file: `data/items.db`

## Setup (Windows)

1. Create and activate a virtual environment (optional but recommended):

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the server:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

4. Ingest Sheet 2 into SQLite (run once or whenever the Excel changes):

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/ingest" | ConvertTo-Json
```

## API Endpoints

- `GET /health` – Service health and current row count (if table exists)
- `POST /ingest` – Load Sheet 2 from the Excel into SQLite `items` table
- `GET /columns` – List columns in `items`
- `GET /items?limit=50&offset=0` – Paginated items
- `GET /items/{id}` – Get a single item by `id`

## Notes

- The `id` column is created from the DataFrame index (1..N) during ingestion for stable row addressing.
- Column names are normalized (lowercased, spaces and symbols replaced with `_`) to be SQLite-friendly.
- If you update the Excel, re-run `POST /ingest` to refresh the table.
