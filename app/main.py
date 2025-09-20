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
    table_name: Optional[str] = None   # Defaults to 'items' if not provided
    map_to_items: Optional[bool] = False  # If true and table_name != 'items', verify row alignment


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
    table_name = req.table_name or "items"

    path = Path(excel_path)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Excel file not found: {excel_path}")

    engine = get_engine()
    result = load_excel_to_sqlite(engine, str(path), sheet_index=sheet_index, table_name=table_name)

    response: Dict[str, Any] = {"message": "Ingestion complete", **result}

    # If requested, verify mapping to items by shared id/sequence
    if req.map_to_items and table_name != "items":
        items_exists = table_exists(engine, "items")
        response["items_table_exists"] = items_exists
        if items_exists:
            items_count = get_row_count(engine, "items") or 0
            new_count = get_row_count(engine, table_name) or 0
            response["items_row_count"] = items_count
            response["new_table_row_count"] = new_count
            response["mapped_by_sequence"] = (items_count == new_count)
            if items_count != new_count:
                response["warning"] = (
                    "Row counts differ between 'items' and the new table; mapping by id may be inconsistent."
                )
            else:
                # Create or replace a view that joins items with the new table by id
                # Aliasing new table's non-id columns with table-prefixed names to avoid collisions
                view_name = f"items_with_{table_name}"
                with engine.begin() as conn:
                    # Get columns of the new table
                    cols = [row[1] for row in conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()]
                    prefix = f"{table_name}_"
                    select_aliases = []
                    for c in cols:
                        if c == "id":
                            continue
                        alias = f"{prefix}{c}"
                        # Quote identifiers with double quotes for safety
                        select_aliases.append(f"ca.\"{c}\" AS \"{alias}\"")

                    select_sql = ", ".join(["i.*"] + select_aliases) if select_aliases else "i.*"

                    # Drop and recreate the view to reflect latest schema
                    conn.execute(text(f"DROP VIEW IF EXISTS \"{view_name}\""))
                    conn.execute(text(
                        f"CREATE VIEW \"{view_name}\" AS "
                        f"SELECT {select_sql} FROM items i LEFT JOIN {table_name} ca ON ca.id = i.id"
                    ))

                response["view_created"] = True
                response["view_name"] = view_name
        else:
            response["warning"] = "Base table 'items' does not exist; mapping-by-sequence could not be verified."

    return response


@app.get("/rename_q")
async def rename_column_q(
    table_name: str,
    old_name: str,
    new_name: str,
    recreate_view: bool = True,
) -> Dict[str, Any]:
    engine = get_engine()

    with engine.begin() as conn:
        # Check table exists and gather columns
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' does not exist")
        cols = [r[1] for r in rows]
        if old_name not in cols:
            raise HTTPException(status_code=404, detail=f"Column '{old_name}' not found in '{table_name}'")
        if new_name in cols:
            raise HTTPException(status_code=400, detail=f"Column '{new_name}' already exists in '{table_name}'")

        # Rename column
        conn.execute(text(f"ALTER TABLE \"{table_name}\" RENAME COLUMN \"{old_name}\" TO \"{new_name}\""))

        # Refresh columns after rename
        rows2 = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        new_cols = [r[1] for r in rows2]

    response: Dict[str, Any] = {
        "message": "Column renamed",
        "table": table_name,
        "old_name": old_name,
        "new_name": new_name,
        "columns": new_cols,
    }

    # Optionally recreate the joined view if this is a secondary table
    if recreate_view and table_name != "items":
        engine = get_engine()
        items_exists = table_exists(engine, "items")
        response["items_table_exists"] = items_exists
        if items_exists:
            items_count = get_row_count(engine, "items") or 0
            new_count = get_row_count(engine, table_name) or 0
            response["items_row_count"] = items_count
            response["new_table_row_count"] = new_count
            response["mapped_by_sequence"] = (items_count == new_count)
            if items_count == new_count:
                view_name = f"items_with_{table_name}"
                with engine.begin() as conn:
                    cols = [row[1] for row in conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()]
                    prefix = f"{table_name}_"
                    select_aliases = []
                    for c in cols:
                        if c == "id":
                            continue
                        alias = f"{prefix}{c}"
                        select_aliases.append(f"ca.\"{c}\" AS \"{alias}\"")
                    select_sql = ", ".join(["i.*"] + select_aliases) if select_aliases else "i.*"
                    conn.execute(text(f"DROP VIEW IF EXISTS \"{view_name}\""))
                    conn.execute(text(
                        f"CREATE VIEW \"{view_name}\" AS "
                        f"SELECT {select_sql} FROM items i LEFT JOIN {table_name} ca ON ca.id = i.id"
                    ))
                response["view_recreated"] = True
                response["view_name"] = view_name
            else:
                response["warning"] = "Row counts differ; view not recreated due to potential id mismatch."

    return response

@app.get("/ingest_q")
async def ingest_q(
    excel_path: Optional[str] = None,
    sheet_index: Optional[int] = None,
    table_name: Optional[str] = None,
    map_to_items: bool = False,
) -> Dict[str, Any]:
    # Mirror the POST /ingest behavior using query params
    excel_path = excel_path or DEFAULT_EXCEL_PATH
    sheet_index = DEFAULT_SHEET_INDEX if sheet_index is None else sheet_index
    table_name = table_name or "items"

    path = Path(excel_path)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Excel file not found: {excel_path}")

    engine = get_engine()
    result = load_excel_to_sqlite(engine, str(path), sheet_index=sheet_index, table_name=table_name)

    response: Dict[str, Any] = {"message": "Ingestion complete", **result}

    if map_to_items and table_name != "items":
        items_exists = table_exists(engine, "items")
        response["items_table_exists"] = items_exists
        if items_exists:
            items_count = get_row_count(engine, "items") or 0
            new_count = get_row_count(engine, table_name) or 0
            response["items_row_count"] = items_count
            response["new_table_row_count"] = new_count
            response["mapped_by_sequence"] = (items_count == new_count)
            if items_count != new_count:
                response["warning"] = (
                    "Row counts differ between 'items' and the new table; mapping by id may be inconsistent."
                )
            else:
                view_name = f"items_with_{table_name}"
                with engine.begin() as conn:
                    cols = [row[1] for row in conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()]
                    prefix = f"{table_name}_"
                    select_aliases = []
                    for c in cols:
                        if c == "id":
                            continue
                        alias = f"{prefix}{c}"
                        select_aliases.append(f"ca.\"{c}\" AS \"{alias}\"")
                    select_sql = ", ".join(["i.*"] + select_aliases) if select_aliases else "i.*"
                    conn.execute(text(f"DROP VIEW IF EXISTS \"{view_name}\""))
                    conn.execute(text(
                        f"CREATE VIEW \"{view_name}\" AS "
                        f"SELECT {select_sql} FROM items i LEFT JOIN {table_name} ca ON ca.id = i.id"
                    ))
                response["view_created"] = True
                response["view_name"] = view_name
        else:
            response["warning"] = "Base table 'items' does not exist; mapping-by-sequence could not be verified."

    return response

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


@app.get("/tables")
async def list_tables() -> Dict[str, List[str]]:
    engine = get_engine()
    with engine.connect() as conn:
        tables = [r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")).fetchall()]
        views = [r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")).fetchall()]
    return {"tables": tables, "views": views}


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
