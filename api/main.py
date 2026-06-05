"""
api/main.py
===========
FastAPI backend for Bagong Enerhiya.

Exposes three endpoints that the Streamlit frontend (and any external
researcher) can query against the SQLite corpus database.

Endpoints
---------
GET /papers
    List papers with optional filtering by tier, year range, and
    full-text keyword search across title and abstract.

GET /papers/{paper_id}
    Full metadata for a single paper, including all extracted properties.

GET /properties
    All extracted properties, filterable by property_type and tier.
    Designed for the cross-paper comparison table in the Streamlit UI.

Running locally
---------------
    uvicorn api.main:app --reload --port 8000

    # Or from project root:
    python -m uvicorn api.main:app --reload --port 8000

API docs auto-generated at:
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc  (ReDoc)
"""

import pathlib
import sqlite3
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Bagong Enerhiya API",
    description=(
        "Open research data API for Philippine macroalgae supercapacitor "
        "literature. Returns paper metadata and AI-extracted material "
        "properties from the Bagong Enerhiya corpus."
    ),
    version="0.1.0",
    license_info={"name": "MIT"},
)

# Allow the Streamlit frontend (any origin during local dev) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_PATH = (
    pathlib.Path(__file__).parent.parent / "db" / "bagong_enerhiya.db"
)

VALID_TIERS = {"core", "supporting", "tangential"}
VALID_PROPERTY_TYPES = {
    "specific_capacitance",
    "BET_surface_area",
    "pyrolysis_temp",
    "activating_agent",
    "heteroatom_content",
    "cycling_stability",
    "energy_density",
    "power_density",
}


@contextmanager
def get_db():
    """Yield a read-only SQLite connection and close it on exit."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row   # allows dict-style column access
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


# ---------------------------------------------------------------------------
# GET /papers
# ---------------------------------------------------------------------------
@app.get(
    "/papers",
    summary="List papers",
    response_description="Filtered list of corpus papers",
)
def list_papers(
    tier: str | None = Query(
        default=None,
        description="Filter by tier: core, supporting, or tangential",
    ),
    year_from: int | None = Query(
        default=None,
        description="Include papers published from this year onwards",
    ),
    year_to: int | None = Query(
        default=None,
        description="Include papers published up to and including this year",
    ),
    open_access: bool | None = Query(
        default=None,
        description="If true, return only open-access papers",
    ),
    keyword: str | None = Query(
        default=None,
        description="Full-text search across title and abstract (case-insensitive)",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of results (default 50, max 200)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Pagination offset",
    ),
) -> dict:
    # Validate tier value early so the error message is clear
    if tier and tier not in VALID_TIERS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid tier '{tier}'. Must be one of: {sorted(VALID_TIERS)}",
        )

    conditions: list[str] = []
    params: list[Any] = []

    if tier:
        conditions.append("tier = ?")
        params.append(tier)

    if year_from is not None:
        conditions.append("year >= ?")
        params.append(year_from)

    if year_to is not None:
        conditions.append("year <= ?")
        params.append(year_to)

    if open_access is not None:
        conditions.append("open_access = ?")
        params.append(1 if open_access else 0)

    if keyword:
        conditions.append(
            "(LOWER(title) LIKE ? OR LOWER(abstract) LIKE ?)"
        )
        term = f"%{keyword.lower()}%"
        params.extend([term, term])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_db() as conn:
        # Total count for pagination metadata
        count_row = conn.execute(
            f"SELECT COUNT(*) AS total FROM papers {where_clause}",
            params,
        ).fetchone()
        total = count_row["total"]

        rows = conn.execute(
            f"""
            SELECT id, title, authors, year, journal, doi,
                   tier, open_access, created_at
            FROM papers
            {where_clause}
            ORDER BY year DESC, id ASC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [row_to_dict(r) for r in rows],
    }


# ---------------------------------------------------------------------------
# GET /papers/{paper_id}
# ---------------------------------------------------------------------------
@app.get(
    "/papers/{paper_id}",
    summary="Get a single paper with its extracted properties",
    response_description="Paper metadata and all extracted properties",
)
def get_paper(paper_id: int) -> dict:
    with get_db() as conn:
        paper_row = conn.execute(
            "SELECT * FROM papers WHERE id = ?",
            (paper_id,),
        ).fetchone()

        if paper_row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Paper with id={paper_id} not found.",
            )

        property_rows = conn.execute(
            """
            SELECT id, property_type, value, unit, conditions,
                   confidence, extraction_method, created_at
            FROM properties
            WHERE paper_id = ?
            ORDER BY property_type, confidence DESC
            """,
            (paper_id,),
        ).fetchall()

    paper = row_to_dict(paper_row)
    paper["properties"] = [row_to_dict(r) for r in property_rows]
    return paper


# ---------------------------------------------------------------------------
# GET /properties
# ---------------------------------------------------------------------------
@app.get(
    "/properties",
    summary="List extracted properties across all papers",
    response_description=(
        "Cross-paper property table for comparison views"
    ),
)
def list_properties(
    property_type: str | None = Query(
        default=None,
        description=(
            "Filter by property type: specific_capacitance, BET_surface_area, "
            "pyrolysis_temp, activating_agent, heteroatom_content, "
            "cycling_stability, energy_density, power_density"
        ),
    ),
    tier: str | None = Query(
        default=None,
        description="Filter by paper tier: core, supporting, or tangential",
    ),
    min_confidence: float = Query(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum extraction confidence score (0.0–1.0)",
    ),
    extraction_method: str | None = Query(
        default=None,
        description="Filter by extraction method: manual, nlp, or llm",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Maximum number of results (default 100, max 500)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Pagination offset",
    ),
) -> dict:
    if property_type and property_type not in VALID_PROPERTY_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid property_type '{property_type}'. "
                f"Must be one of: {sorted(VALID_PROPERTY_TYPES)}"
            ),
        )

    if tier and tier not in VALID_TIERS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid tier '{tier}'. Must be one of: {sorted(VALID_TIERS)}",
        )

    conditions: list[str] = ["pr.confidence >= ?"]
    params: list[Any] = [min_confidence]

    if property_type:
        conditions.append("pr.property_type = ?")
        params.append(property_type)

    if tier:
        conditions.append("p.tier = ?")
        params.append(tier)

    if extraction_method:
        conditions.append("pr.extraction_method = ?")
        params.append(extraction_method)

    where_clause = f"WHERE {' AND '.join(conditions)}"

    with get_db() as conn:
        count_row = conn.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM properties pr
            JOIN papers p ON p.id = pr.paper_id
            {where_clause}
            """,
            params,
        ).fetchone()
        total = count_row["total"]

        rows = conn.execute(
            f"""
            SELECT
                pr.id,
                pr.paper_id,
                p.title        AS paper_title,
                p.authors      AS paper_authors,
                p.year         AS paper_year,
                p.tier         AS paper_tier,
                p.doi          AS paper_doi,
                pr.property_type,
                pr.value,
                pr.unit,
                pr.conditions,
                pr.confidence,
                pr.extraction_method
            FROM properties pr
            JOIN papers p ON p.id = pr.paper_id
            {where_clause}
            ORDER BY pr.property_type, p.year DESC, pr.confidence DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [row_to_dict(r) for r in rows],
    }


# ---------------------------------------------------------------------------
# GET / — health check
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "project": "Bagong Enerhiya",
        "status": "ok",
        "docs": "/docs",
    }