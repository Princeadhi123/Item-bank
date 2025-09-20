from __future__ import annotations

import re
from typing import Dict, List, Tuple

import pandas as pd
from sqlalchemy.engine import Engine


DEFAULT_SHEET_INDEX = 1  # 0-based; Sheet 2


def _normalize_column(name: str) -> str:
    # Lowercase, trim, replace non-alphanum with underscores, collapse repeats
    n = name.strip().lower()
    n = re.sub(r"[^0-9a-zA-Z]+", "_", n)
    n = re.sub(r"_+", "_", n)
    n = n.strip("_")
    if n == "":
        n = "col"
    # Avoid reserved name 'id' collision by leaving as-is; we add index as id
    return n


def _dedupe_columns(cols: List[str]) -> List[str]:
    seen = {}
    out = []
    for c in cols:
        base = c
        i = seen.get(base, 0)
        if i == 0 and base not in seen:
            out.append(base)
            seen[base] = 1
        else:
            i = seen.get(base, 1)
            while True:
                candidate = f"{base}_{i}"
                if candidate not in seen:
                    out.append(candidate)
                    seen[base] = i + 1
                    seen[candidate] = 1
                    break
                i += 1
    return out


def load_excel_to_sqlite(
    engine: Engine,
    excel_path: str,
    sheet_index: int = DEFAULT_SHEET_INDEX,
    table_name: str = "items",
) -> Dict:
    """Load the specified sheet from Excel into SQLite as `table_name`.

    - Normalizes column names to SQLite-friendly snake_case
    - Replaces the table if it exists
    - Adds an integer `id` column from the DataFrame index (1..N)
    """
    # Read Excel
    df = pd.read_excel(excel_path, sheet_name=sheet_index, engine="openpyxl")

    # Normalize column names
    cols = [_normalize_column(str(c)) for c in df.columns]
    cols = _dedupe_columns(cols)
    df.columns = cols

    # Convert NaN to None for SQLite NULL
    df = df.where(pd.notnull(df), None)

    # Create index-based id (1..N)
    df.index = range(1, len(df) + 1)

    # Write to SQLite
    with engine.begin() as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=True, index_label="id")

    return {
        "table": table_name,
        "rows": int(len(df)),
        "columns": list(df.columns),
    }
