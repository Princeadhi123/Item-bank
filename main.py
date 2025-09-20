import os
import sqlite3
from typing import List, Optional, Tuple, Dict, Any

from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "data", "items.db")
STATIC_DIR = os.path.join(APP_DIR, "static")

# Ensure the data directory exists in deployment environments (e.g., Railway)
os.makedirs(os.path.join(APP_DIR, "data"), exist_ok=True)

app = FastAPI(title="Item Bank API", version="1.0")

# If you decide to serve the frontend separately, CORS will help. For now, same origin, but this is harmless.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DB helpers ---

def get_conn() -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        # Create an empty DB file so the app can boot; real data should be provided via items.db.
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            # Minimal placeholder table to make health checks pass; real queries expect full schema.
            conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT)")
        except Exception:
            pass
        return conn
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

CONTENT_AREAS = [
    ("s1_thinking_skills_including_computational_thinking", "S1 Thinking Skills (incl. Computational Thinking)"),
    ("s2_numbers_and_operations", "S2 Numbers & Operations"),
    ("s3_algebra", "S3 Algebra"),
    ("s4_functions", "S4 Functions"),
    ("s5_geometry_and_measurement", "S5 Geometry & Measurement"),
    ("s6_data_handling_statistics_and_probability", "S6 Data Handling, Statistics & Probability"),
]

NUTA_CONTENTS = [
    ("c1_numeric_system", "C1 Numeric System"),
    ("c2_basic_numerical_operations", "C2 Basic Numerical Operations"),
    ("c3_geometry", "C3 Geometry"),
    ("c4_time_and_measures", "C4 Time & Measures"),
    ("c5_fractions", "C5 Fractions"),
    ("c6_decimal_numbers", "C6 Decimal Numbers"),
    ("c7_percentages", "C7 Percentages"),
    ("c8_circumference_area_and_volume", "C8 Circumference, Area & Volume"),
    ("c9_statistics_and_probability", "C9 Statistics & Probability"),
]

TARGET_AREAS = [
    ("t10", "T10 Mental Calculations & Inferences (S1/S2)"),
    ("t11", "T11 Basic Calcs with Rational Numbers (S2)"),
    ("t12", "T12 Concept of a Real Number (S2)"),
    ("t13", "T13 Proportions & Percentages (S2)"),
    ("t14", "T14 Solves Equations (S3/S4)"),
    ("t15", "T15 Interprets & Forms Functions (S3/S4)"),
    ("t16", "T16 Relations between Geometric Concepts (S5)"),
    ("t17", "T17 Right Triangles & Circles (S5)"),
    ("t18", "T18 Areas & Volumes (S5)"),
    ("t19", "T19 Statistics & Probability (S6)"),
    ("t20", "T20 Algorithmic Thinking & Programming (S1)"),
]

SAFE_SORT_COLUMNS = {
    "id": "i.id",
    "label": "i.label",
    "name": "i.name",
    "name_2": "i.name_2",
    "source": "i.source",
    "type": "it.item_type_all",
    "level": "ih.hierarchical_level_all",
    "meanp_all": "idl.meanp_all_classical",
    "a_irt": "ids.a_irt",
    "meanrit_classical": "ids.meanrit_classical",
    "n": "i.n",
}

# --- Query builders ---

def build_base_select() -> str:
    # Note: items_NuTa_content_area table has mixed case; must be quoted in SQL.
    return (
        "SELECT "
        " i.id, i.label, i.name, i.name_2, i.max, i.n, i.source, "
        " it.item_type_all, ih.hierarchical_level_all, "
        " idl.meanp_all_classical, idl.p_g3_classical, idl.p_g6_classical, idl.p_g8_classical, idl.p_g9_classical, "
        " idl.b_0_1_irt, idl.b01_2_irt, idl.b012_3_irt, idl.b0123_4_irt, idl.se_b_0_1_irt, idl.se_b01_2_irt, idl.se_b012_3_irt, idl.se_b0123_4_irt, "
        " ids.meanrit_classical, ids.meang_classical, ids.meand_classical, ids.meanstd_classical, ids.a_irt, "
        " ic.s1_thinking_skills_including_computational_thinking AS s1, "
        " ic.s2_numbers_and_operations AS s2, ic.s3_algebra AS s3, ic.s4_functions AS s4, "
        " ic.\"s5_geometry_and_measurement\" AS s5, ic.s6_data_handling_statistics_and_probability AS s6, "
        " nt.nuta_skill_level, nt.contents AS nuta_contents, "
        " nt.c1_numeric_system, nt.c2_basic_numerical_operations, nt.c3_geometry, nt.c4_time_and_measures, nt.c5_fractions, nt.c6_decimal_numbers, nt.c7_percentages, nt.c8_circumference_area_and_volume, nt.c9_statistics_and_probability, "
        " ta.t10_performs_mental_calculations_and_makes_inferences_related_to_s1_and_s2 AS t10, "
        " ta.t11_performs_basic_calculations_with_rational_numbers_related_to_s2 AS t11, "
        " ta.t12_understands_the_concept_of_a_real_number_related_to_s2 AS t12, "
        " ta.t13_calculates_proportions_numbers_referring_to_percentages_and_percentages_related_to_change_and_comparison_related_to_s2 AS t13, "
        " ta.t14_solves_equations_related_to_s3_and_s4 AS t14, "
        " ta.t15_interprets_and_forms_functions_related_to_s3_and_s4 AS t15, "
        " ta.t16_understands_relations_between_geometric_concepts_related_to_s5 AS t16, "
        " ta.t17_utilizes_properties_related_to_right_triangles_and_circles_related_to_s5 AS t17, "
        " ta.t18_calculates_areas_and_volumes_related_to_s5 AS t18, "
        " ta.t19_determines_statistical_measures_and_calculates_probabilities_related_to_s6 AS t19, "
        " ta.t20_applies_algorithmic_thinking_and_problem_solving_including_through_programming_related_to_s1 AS t20 "
        "FROM items i "
        "LEFT JOIN items_type it ON it.id = i.id "
        "LEFT JOIN items_hierarchical_level ih ON ih.id = i.id "
        "LEFT JOIN items_difficulty_level idl ON idl.id = i.id "
        "LEFT JOIN items_discrimination ids ON ids.id = i.id "
        "LEFT JOIN items_content_area ic ON ic.id = i.id "
        "LEFT JOIN \"items_NuTa_content_area\" nt ON nt.id = i.id "
        "LEFT JOIN items_target_area ta ON ta.id = i.id "
    )


def build_where_clauses(
    search: Optional[str] = None,
    item_types: Optional[List[str]] = None,
    levels: Optional[List[str]] = None,
    content_areas: Optional[List[str]] = None,  # expects list of s1..s6
    target_areas: Optional[List[str]] = None,  # expects t10..t20
    nuta_levels: Optional[List[str]] = None,
    sources: Optional[List[str]] = None,
    meanp_min: Optional[float] = None,
    meanp_max: Optional[float] = None,
    a_irt_min: Optional[float] = None,
    a_irt_max: Optional[float] = None,
    meanrit_min: Optional[float] = None,
    meanrit_max: Optional[float] = None,
) -> Tuple[List[str], List[Any]]:
    clauses: List[str] = []
    params: List[Any] = []

    # Map short keys to actual SQL columns to avoid relying on SELECT aliases in WHERE
    content_area_map = {
        "s1": "ic.s1_thinking_skills_including_computational_thinking",
        "s2": "ic.s2_numbers_and_operations",
        "s3": "ic.s3_algebra",
        "s4": "ic.s4_functions",
        "s5": "ic.\"s5_geometry_and_measurement\"",
        "s6": "ic.s6_data_handling_statistics_and_probability",
    }
    target_area_map = {
        "t10": "ta.t10_performs_mental_calculations_and_makes_inferences_related_to_s1_and_s2",
        "t11": "ta.t11_performs_basic_calculations_with_rational_numbers_related_to_s2",
        "t12": "ta.t12_understands_the_concept_of_a_real_number_related_to_s2",
        "t13": "ta.t13_calculates_proportions_numbers_referring_to_percentages_and_percentages_related_to_change_and_comparison_related_to_s2",
        "t14": "ta.t14_solves_equations_related_to_s3_and_s4",
        "t15": "ta.t15_interprets_and_forms_functions_related_to_s3_and_s4",
        "t16": "ta.t16_understands_relations_between_geometric_concepts_related_to_s5",
        "t17": "ta.t17_utilizes_properties_related_to_right_triangles_and_circles_related_to_s5",
        "t18": "ta.t18_calculates_areas_and_volumes_related_to_s5",
        "t19": "ta.t19_determines_statistical_measures_and_calculates_probabilities_related_to_s6",
        "t20": "ta.t20_applies_algorithmic_thinking_and_problem_solving_including_through_programming_related_to_s1",
    }

    if search:
        like = f"%{search}%"
        clauses.append(
            "(i.label LIKE ? OR i.name LIKE ? OR i.source LIKE ? OR nt.contents LIKE ?)"
        )
        params.extend([like, like, like, like])

    if item_types:
        placeholders = ",".join(["?"] * len(item_types))
        clauses.append(f"it.item_type_all IN ({placeholders})")
        params.extend(item_types)

    if levels:
        placeholders = ",".join(["?"] * len(levels))
        clauses.append(f"ih.hierarchical_level_all IN ({placeholders})")
        params.extend(levels)

    if content_areas:
        cols = []
        for ca in content_areas:
            key = (ca or "").lower().strip()
            if key not in content_area_map:
                raise HTTPException(status_code=400, detail="Invalid content_area; use s1..s6")
            cols.append(content_area_map[key])
        if cols:
            or_clause = " OR ".join([f"COALESCE({c}, 0) > 0" for c in cols])
            clauses.append(f"({or_clause})")

    if target_areas:
        cols = []
        for t in target_areas:
            tkey = (t or "").lower().strip()
            if tkey not in target_area_map:
                raise HTTPException(status_code=400, detail="Invalid target area key")
            cols.append(target_area_map[tkey])
        if cols:
            or_clause = " OR ".join([f"COALESCE({c}, 0) > 0" for c in cols])
            clauses.append(f"({or_clause})")

    if nuta_levels:
        placeholders = ",".join(["?"] * len(nuta_levels))
        clauses.append(f"nt.nuta_skill_level IN ({placeholders})")
        params.extend(nuta_levels)

    if sources:
        placeholders = ",".join(["?"] * len(sources))
        clauses.append(f"i.source IN ({placeholders})")
        params.extend(sources)

    if meanp_min is not None:
        clauses.append("idl.meanp_all_classical >= ?")
        params.append(meanp_min)
    if meanp_max is not None:
        clauses.append("idl.meanp_all_classical <= ?")
        params.append(meanp_max)

    if a_irt_min is not None:
        clauses.append("ids.a_irt >= ?")
        params.append(a_irt_min)
    if a_irt_max is not None:
        clauses.append("ids.a_irt <= ?")
        params.append(a_irt_max)

    if meanrit_min is not None:
        clauses.append("ids.meanrit_classical >= ?")
        params.append(meanrit_min)
    if meanrit_max is not None:
        clauses.append("ids.meanrit_classical <= ?")
        params.append(meanrit_max)

    return clauses, params


def dominant_content_area(row: sqlite3.Row) -> Optional[str]:
    # Determine dominant content area label by max value among s1..s6
    values = [(row["s1"], CONTENT_AREAS[0][1]), (row["s2"], CONTENT_AREAS[1][1]), (row["s3"], CONTENT_AREAS[2][1]),
              (row["s4"], CONTENT_AREAS[3][1]), (row["s5"], CONTENT_AREAS[4][1]), (row["s6"], CONTENT_AREAS[5][1])]
    max_val = None
    max_label = None
    for v, label in values:
        try:
            fv = float(v) if v is not None else 0.0
        except Exception:
            fv = 0.0
        if max_val is None or fv > max_val:
            max_val = fv
            max_label = label
    if max_val is None or max_val <= 0:
        return None
    return max_label


@app.get("/api/items")
def list_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    item_type: Optional[List[str]] = Query(None),
    level: Optional[List[str]] = Query(None),
    content_area: Optional[List[str]] = Query(None),
    target_area: Optional[List[str]] = Query(None),
    nuta_skill_level: Optional[List[str]] = Query(None),
    source: Optional[List[str]] = Query(None),
    meanp_min: Optional[float] = None,
    meanp_max: Optional[float] = None,
    a_irt_min: Optional[float] = None,
    a_irt_max: Optional[float] = None,
    meanrit_min: Optional[float] = None,
    meanrit_max: Optional[float] = None,
    sort_by: str = Query("id"),
    sort_dir: str = Query("asc"),
):
    base = build_base_select()
    where_clauses, params = build_where_clauses(
        search=search,
        item_types=item_type,
        levels=level,
        content_areas=content_area,
        target_areas=target_area,
        nuta_levels=nuta_skill_level,
        sources=source,
        meanp_min=meanp_min,
        meanp_max=meanp_max,
        a_irt_min=a_irt_min,
        a_irt_max=a_irt_max,
        meanrit_min=meanrit_min,
        meanrit_max=meanrit_max,
    )

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    sort_col = SAFE_SORT_COLUMNS.get(sort_by, "i.id")
    sort_direction = "DESC" if str(sort_dir).lower() == "desc" else "ASC"

    limit_offset = " LIMIT ? OFFSET ?"
    params_with_paging = list(params) + [page_size, (page - 1) * page_size]

    sql = base + where_sql + f" ORDER BY {sort_col} {sort_direction}" + limit_offset
    # Count distinct item IDs to avoid duplicates from LEFT JOINs
    count_sql = "SELECT COUNT(DISTINCT t.id) as cnt FROM (" + base + where_sql + ") AS t"

    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute(sql, params_with_paging).fetchall()
        total = cur.execute(count_sql, params).fetchone()[0]

    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "label": r["label"],
            "name": r["name"],
            "source": r["source"],
            "item_type_all": r["item_type_all"],
            "hierarchical_level_all": r["hierarchical_level_all"],
            "meanp_all_classical": r["meanp_all_classical"],
            "meanrit_classical": r["meanrit_classical"],
            "a_irt": r["a_irt"],
            "dominant_content_area": dominant_content_area(r),
        })

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "items": items,
    }


@app.get("/api/items/{item_id}")
def get_item(item_id: int):
    base = build_base_select()
    sql = base + " WHERE i.id = ? LIMIT 1"
    with get_conn() as conn:
        row = conn.execute(sql, (item_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")

    # Build detailed response
    content_areas = {
        "S1": float(row["s1"]) if row["s1"] is not None else 0,
        "S2": float(row["s2"]) if row["s2"] is not None else 0,
        "S3": float(row["s3"]) if row["s3"] is not None else 0,
        "S4": float(row["s4"]) if row["s4"] is not None else 0,
        "S5": float(row["s5"]) if row["s5"] is not None else 0,
        "S6": float(row["s6"]) if row["s6"] is not None else 0,
    }

    nuta_contents = { key: float(row[key]) if row[key] is not None else 0 for key, _ in NUTA_CONTENTS }
    targets = { f"t{i}": float(row[f"t{i}"]) if row[f"t{i}"] is not None else 0 for i in range(10, 21) }

    return {
        "id": row["id"],
        "label": row["label"],
        "name": row["name"],
        "name_2": row["name_2"],
        "max": row["max"],
        "n": row["n"],
        "source": row["source"],
        "type": row["item_type_all"],
        "hierarchical_level": row["hierarchical_level_all"],
        "difficulty": {
            "meanp_all_classical": row["meanp_all_classical"],
            "p_g3_classical": row["p_g3_classical"],
            "p_g6_classical": row["p_g6_classical"],
            "p_g8_classical": row["p_g8_classical"],
            "p_g9_classical": row["p_g9_classical"],
            "b_0_1_irt": row["b_0_1_irt"],
            "b01_2_irt": row["b01_2_irt"],
            "b012_3_irt": row["b012_3_irt"],
            "b0123_4_irt": row["b0123_4_irt"],
            "se_b_0_1_irt": row["se_b_0_1_irt"],
            "se_b01_2_irt": row["se_b01_2_irt"],
            "se_b012_3_irt": row["se_b012_3_irt"],
            "se_b0123_4_irt": row["se_b0123_4_irt"],
        },
        "discrimination": {
            "meanrit_classical": row["meanrit_classical"],
            "meang_classical": row["meang_classical"],
            "meand_classical": row["meand_classical"],
            "meanstd_classical": row["meanstd_classical"],
            "a_irt": row["a_irt"],
        },
        "content_area": content_areas,
        "nuta": {
            "nuta_skill_level": row["nuta_skill_level"],
            "contents": row["nuta_contents"],
            "weights": nuta_contents,
        },
        "targets": targets,
        "dominant_content_area": dominant_content_area(row),
    }


@app.get("/api/filters")
def get_filters():
    with get_conn() as conn:
        cur = conn.cursor()
        item_types = [r[0] for r in cur.execute("SELECT DISTINCT item_type_all FROM items_type WHERE item_type_all IS NOT NULL ORDER BY 1").fetchall()]
        levels = [r[0] for r in cur.execute("SELECT DISTINCT hierarchical_level_all FROM items_hierarchical_level WHERE hierarchical_level_all IS NOT NULL ORDER BY 1").fetchall()]
        nuta_levels = [r[0] for r in cur.execute("SELECT DISTINCT nuta_skill_level FROM \"items_NuTa_content_area\" WHERE nuta_skill_level IS NOT NULL ORDER BY 1").fetchall()]
        sources = [r[0] for r in cur.execute("SELECT DISTINCT source FROM items WHERE source IS NOT NULL ORDER BY 1").fetchall()]

    return {
        "item_types": item_types,
        "hierarchical_levels": levels,
        "nuta_skill_levels": nuta_levels,
        "sources": sources,
        "content_areas": [
            {"key": "s1", "label": CONTENT_AREAS[0][1]},
            {"key": "s2", "label": CONTENT_AREAS[1][1]},
            {"key": "s3", "label": CONTENT_AREAS[2][1]},
            {"key": "s4", "label": CONTENT_AREAS[3][1]},
            {"key": "s5", "label": CONTENT_AREAS[4][1]},
            {"key": "s6", "label": CONTENT_AREAS[5][1]},
        ],
        "target_areas": [
            {"key": key, "label": label} for key, label in TARGET_AREAS
        ],
    }


# Serve static files (frontend)
if os.path.isdir(STATIC_DIR):
    # Serve assets from /static
    app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")

# Serve index.html at root (always register the route)
@app.get("/")
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"detail": "Index file not found"})


# Serve favicon (avoids noisy 404s and works if a favicon exists in /static)
@app.get("/favicon.ico")
def favicon():
    icon_path = os.path.join(STATIC_DIR, "favicon.ico")
    if os.path.exists(icon_path):
        return FileResponse(icon_path)
    return Response(status_code=204)


# Optional: health check
@app.get("/api/health")
def health():
    try:
        with get_conn() as _:
            pass
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
