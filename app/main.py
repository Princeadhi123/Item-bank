from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from .db import DB_URL, get_engine, get_row_count, table_exists
from .ingest import DEFAULT_SHEET_INDEX, load_excel_to_sqlite

app = FastAPI(title="Item Bank Backend")

# Default Excel path (Windows)
DEFAULT_EXCEL_PATH = r"c:\\Users\\pdaadh\\Desktop\\Item bank\\Item bank from DigiArvi 2025 - Final.xlsx"


class IngestRequest(BaseModel):
    excel_path: Optional[str] = None
    sheet_index: Optional[int] = None  # 0-based; Sheet 2 is 1


@app.get("/health")
async def health() -> Dict[str, Any]:
    engine = get_engine()
    count = get_row_count(engine, "items")
    return {
        "status": "ok",
        "db_url": DB_URL,
        "items_table_exists": table_exists(engine, "items"),
        "row_count": count,
    }


@app.post("/ingest")
async def ingest(req: IngestRequest) -> Dict[str, Any]:
    excel_path = req.excel_path or DEFAULT_EXCEL_PATH
    sheet_index = DEFAULT_SHEET_INDEX if req.sheet_index is None else req.sheet_index

    path = Path(excel_path)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Excel file not found: {excel_path}")

    engine = get_engine()
    result = load_excel_to_sqlite(engine, str(path), sheet_index=sheet_index, table_name="items")
    return {"message": "Ingestion complete", **result}


@app.get("/columns")
async def list_columns() -> Dict[str, List[str]]:
    engine = get_engine()
    if not table_exists(engine, "items"):
        raise HTTPException(status_code=404, detail="Table 'items' does not exist. Run POST /ingest first.")

    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(items)")).fetchall()
        # rows: cid, name, type, notnull, dflt_value, pk
        cols = [r[1] for r in rows]
    return {"columns": cols}


@app.get("/items")
async def list_items(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    engine = get_engine()
    if not table_exists(engine, "items"):
        raise HTTPException(status_code=404, detail="Table 'items' does not exist. Run POST /ingest first.")

    with engine.connect() as conn:
        data = conn.execute(text("SELECT * FROM items ORDER BY id ASC LIMIT :limit OFFSET :offset"), {"limit": limit, "offset": offset}).mappings().all()
        total = get_row_count(engine, "items") or 0
    return {"total": total, "count": len(data), "items": [dict(row) for row in data]}


@app.get("/items/{item_id}")
async def get_item(item_id: int) -> Dict[str, Any]:
    engine = get_engine()
    if not table_exists(engine, "items"):
        raise HTTPException(status_code=404, detail="Table 'items' does not exist. Run POST /ingest first.")

    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM items WHERE id = :id"), {"id": item_id}).mappings().fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Item with id={item_id} not found")
    return dict(row)
