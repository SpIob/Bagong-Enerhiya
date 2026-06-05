"""
ingest/search_papers.py
=======================
Expands the corpus by querying the Semantic Scholar API with anchor
keywords and inserting new papers into bagong_enerhiya.db.

Reads the API key from apis.txt (one key per line, prefixed with
"semantic_scholar="). apis.txt is .gitignore'd and never committed.

Target: bring the corpus from 14 to ~30 papers.

Usage
-----
    python ingest/search_papers.py                  # dry-run: print results
    python ingest/search_papers.py --insert         # insert into database
    python ingest/search_papers.py --insert --limit 5   # 5 results per query
    python ingest/search_papers.py --insert --db path/to/other.db

Semantic Scholar API
--------------------
- Base URL : https://api.semanticscholar.org/graph/v1
- Endpoint : /paper/search
- Key      : passed as x-api-key header (100 req/5 min with key)
- Docs     : https://api.semanticscholar.org/api-docs/graph
"""

import argparse
import html
import json
import pathlib
import re
import sqlite3
import time

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"

# Fields requested from the API — keeps response payload small
PAPER_FIELDS = "title,authors,year,journal,externalIds,abstract,isOpenAccess"

# Polite delay between requests (seconds)
REQUEST_DELAY = 1.5

# Keyword queries — each maps to a default tier for new papers found
SEARCH_QUERIES: list[dict] = [
    {
        "query": "seaweed macroalgae biochar supercapacitor",
        "tier": "supporting",          # was "core" — results too mixed
    },
    {
        "query": "Sargassum Gracilaria Ulva carbon electrode supercapacitor",
        "tier": "core",
    },
    # Query 3 removed — Kappaphycus/Eucheuma electrode papers don't exist yet
    {
        "query": "seaweed derived nitrogen doped carbon supercapacitor",
        "tier": "core",
    },
    {
        "query": "macroalgae pyrolysis activated carbon electrochemical",
        "tier": "supporting",
    },
    {
        "query": "biomass KOH activated carbon supercapacitor seaweed",
        "tier": "supporting",
    },
]

# DOIs already in the database — used to skip known papers before insertion
# (the UNIQUE constraint catches duplicates too, but this avoids noisy output)
EXISTING_DOIS: set[str] = set()


# ---------------------------------------------------------------------------
# API key loader
# ---------------------------------------------------------------------------
def load_api_key(apis_path: pathlib.Path) -> str | None:
    """
    Read the Semantic Scholar API key from apis.txt.
    Expected format (one entry per line):
        semantic_scholar=your_key_here
    Returns None if the file or key is missing (unauthenticated requests
    still work but are rate-limited to 1 req/sec).
    """
    if not apis_path.exists():
        print(f"  [WARN] {apis_path} not found — running unauthenticated.")
        return None

    for line in apis_path.read_text().splitlines():
        line = line.strip()
        if line.startswith("semantic_scholar="):
            key = line.split("=", 1)[1].strip()
            return key if key else None

    print("  [WARN] semantic_scholar key not found in apis.txt — running unauthenticated.")
    return None


# ---------------------------------------------------------------------------
# Semantic Scholar helpers
# ---------------------------------------------------------------------------
def build_headers(api_key: str | None) -> dict:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def search_semantic_scholar(
    query: str,
    api_key: str | None,
    limit: int,
) -> list[dict]:
    """
    Query the Semantic Scholar /paper/search endpoint.
    Returns a list of raw paper dicts from the API response.
    """
    url = f"{SEMANTIC_SCHOLAR_BASE}/paper/search"
    params = {
        "query":  query,
        "limit":  limit,
        "fields": PAPER_FIELDS,
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=build_headers(api_key),
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [WARN] Semantic Scholar request failed for '{query}': {exc}")
        return []

    return response.json().get("data", [])


def normalise_paper(raw: dict, tier: str) -> dict | None:
    """
    Convert a Semantic Scholar paper dict into the schema expected by
    insert_paper(). Returns None if the paper has no usable title.
    """
    title = html.unescape((raw.get("title") or "").strip())
    if not title:
        return None

    # Authors: list of {name: "..."} objects
    authors = ", ".join(
        a.get("name", "").strip()
        for a in (raw.get("authors") or [])
        if a.get("name")
    )

    year = raw.get("year")

    # Journal: Semantic Scholar nests this as {name: "..."}
    journal_obj = raw.get("journal") or {}
    journal = html.unescape((journal_obj.get("name") or "").strip())

    # DOI: nested under externalIds
    external_ids = raw.get("externalIds") or {}
    doi = external_ids.get("DOI") or external_ids.get("doi")
    if doi:
        doi = doi.strip()

    abstract = html.unescape(
        re.sub(r"<[^>]+>", "", raw.get("abstract") or "").strip()
    )

    open_access = 1 if raw.get("isOpenAccess") else 0

    return {
        "title":       title,
        "authors":     authors,
        "year":        year,
        "journal":     journal,
        "doi":         doi,
        "abstract":    abstract,
        "tier":        tier,
        "open_access": open_access,
    }


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def ensure_schema(conn: sqlite3.Connection, schema_path: pathlib.Path) -> None:
    """Apply schema.sql if tables don't exist yet (idempotent)."""
    conn.executescript(schema_path.read_text())


def load_existing_dois(conn: sqlite3.Connection) -> set[str]:
    """Return the set of DOIs already present in the papers table."""
    rows = conn.execute(
        "SELECT doi FROM papers WHERE doi IS NOT NULL"
    ).fetchall()
    return {row[0].lower() for row in rows}


def insert_paper(conn: sqlite3.Connection, record: dict) -> int | None:
    """
    Insert a paper. Skips silently on DOI collision (UNIQUE constraint).
    Returns the new rowid, or None if skipped.
    """
    try:
        cursor = conn.execute(
            """
            INSERT INTO papers
                (title, authors, year, journal, doi, abstract,
                 tier, open_access)
            VALUES
                (:title, :authors, :year, :journal, :doi, :abstract,
                 :tier, :open_access)
            """,
            record,
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None   # duplicate DOI — silent skip


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def run(
    db_path: str,
    apis_path: pathlib.Path,
    limit_per_query: int,
    insert: bool,
) -> None:
    print("\nBagong Enerhiya — Semantic Scholar Corpus Expansion")
    print(f"Database  : {db_path}")
    print(f"Mode      : {'INSERT' if insert else 'DRY RUN'}")
    print(f"Queries   : {len(SEARCH_QUERIES)}")
    print(f"Max/query : {limit_per_query}")
    print("-" * 60)

    api_key = load_api_key(apis_path)
    print(f"  API key : {'found' if api_key else 'not found (unauthenticated)'}\n")

    # Load existing DOIs for pre-flight duplicate check
    preview_conn = sqlite3.connect(db_path)
    global EXISTING_DOIS
    EXISTING_DOIS = load_existing_dois(preview_conn)
    preview_conn.close()
    print(f"  Existing papers in DB : {len(EXISTING_DOIS)} with DOIs\n")

    # Open write connection only in insert mode
    write_conn = sqlite3.connect(db_path) if insert else None
    if write_conn:
        schema_path = pathlib.Path(db_path).parent.parent / "db" / "schema.sql"
        if not schema_path.exists():
            schema_path = pathlib.Path(db_path).parent / "schema.sql"
        ensure_schema(write_conn, schema_path)

    total_found    = 0
    total_new      = 0
    total_inserted = 0
    total_skipped  = 0

    for query_entry in SEARCH_QUERIES:
        query = query_entry["query"]
        tier  = query_entry["tier"]

        print(f"  [QUERY] \"{query}\"  (tier={tier})")
        raw_results = search_semantic_scholar(query, api_key, limit_per_query)
        time.sleep(REQUEST_DELAY)

        if not raw_results:
            print("          → no results returned\n")
            continue

        new_in_query = 0

        for raw in raw_results:
            record = normalise_paper(raw, tier)
            if not record:
                continue

            total_found += 1
            doi_lower = (record["doi"] or "").lower()

            # Pre-flight duplicate check
            if doi_lower and doi_lower in EXISTING_DOIS:
                total_skipped += 1
                continue

            total_new += 1
            new_in_query += 1

            if not insert:
                # Dry-run: just print
                print(
                    f"          + [{record['year'] or '????'}] "
                    f"{record['title'][:65]}"
                    + (f"  doi={record['doi']}" if record['doi'] else "")
                )
            else:
                rowid = insert_paper(write_conn, record)
                if rowid:
                    total_inserted += 1
                    EXISTING_DOIS.add(doi_lower)
                    print(
                        f"          [OK] id={rowid:>3}  "
                        f"[{record['year'] or '????'}]  "
                        f"{record['title'][:58]}"
                    )
                else:
                    total_skipped += 1

        print(f"          → {new_in_query} new paper(s) from this query\n")

    if write_conn:
        write_conn.close()

    # Summary
    print("-" * 60)
    print(f"Total API results examined : {total_found}")
    print(f"Already in database        : {total_skipped}")
    print(f"New (not yet in database)  : {total_new}")
    if insert:
        print(f"Inserted                   : {total_inserted}")
    else:
        print(f"Would insert               : {total_new}")
        print("\nRe-run with --insert to write to the database.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    project_root = pathlib.Path(__file__).parent.parent

    parser = argparse.ArgumentParser(
        description="Expand corpus via Semantic Scholar keyword search."
    )
    parser.add_argument(
        "--insert",
        action="store_true",
        help="Write new papers to the database (default: dry-run)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="Maximum results per query (default: 10)",
    )
    parser.add_argument(
        "--db",
        default=str(project_root / "db" / "bagong_enerhiya.db"),
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--apis",
        default=str(project_root / "apis.txt"),
        help="Path to the apis.txt file containing the Semantic Scholar key",
    )
    args = parser.parse_args()

    run(
        db_path=args.db,
        apis_path=pathlib.Path(args.apis),
        limit_per_query=args.limit,
        insert=args.insert,
    )