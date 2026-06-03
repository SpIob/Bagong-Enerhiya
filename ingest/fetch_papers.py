"""
ingest/fetch_papers.py
======================
Seeds bagong_enerhiya.db with the 14 corpus papers by fetching their
metadata from the CrossRef API (no key required).

Usage
-----
    python ingest/fetch_papers.py                  # dry-run: print fetched records
    python ingest/fetch_papers.py --insert         # insert into db/bagong_enerhiya.db
    python ingest/fetch_papers.py --insert --db path/to/other.db

CrossRef is used as the primary source because:
  - No API key required
  - Returns clean title, authors, year, journal, and abstract metadata
  - Covers all 14 DOI-identified corpus papers
  - Unlimited free tier

Patents (CN108069426B) have no DOI and are seeded manually as a fallback.
"""

import argparse
import html
import json
import re
import sqlite3
import time
import pathlib
import requests

# ---------------------------------------------------------------------------
# Corpus — 14 papers from the Literature Tracker
# Fields: doi, tier, open_access, manual_abstract (optional fallback)
# ---------------------------------------------------------------------------
CORPUS: list[dict] = [
    # --- Core: seaweed/macroalgae carbon for electrochemical storage ----------
    {
        "doi": "10.3390/ma15165748",
        "tier": "core",
        "open_access": 1,
    },
    {
        "doi": "10.1177/0958305X19882398",
        "tier": "core",
        "open_access": 0,
    },
    {
        "doi": "10.1007/s10934-020-00871-7",
        "tier": "core",
        "open_access": 0,
    },
    {
        "doi": "10.1002/adfm.200801057",
        "tier": "core",
        "open_access": 0,
    },
    {
        "doi": "10.3389/fenrg.2023.1135093",
        "tier": "core",
        "open_access": 1,
    },

    # --- Supporting: pyrolysis, hydrochar, and biochar parameters ------------
    {
        "doi": "10.1007/s13399-022-02365-9",
        "tier": "supporting",
        "open_access": 0,
    },
    {
        "doi": "10.1016/j.biortech.2021.126258",
        "tier": "supporting",
        "open_access": 0,
    },

    # --- Supporting: K. alvarezii characterisation ---------------------------
    {
        "doi": "10.3390/md22110491",
        "tier": "supporting",
        "open_access": 1,
    },
    {
        "doi": "10.1016/j.ijbiomac.2024.135205",
        "tier": "supporting",
        "open_access": 0,
    },

    # --- Tangential: K. alvarezii non-energy applications -------------------
    {
        "doi": "10.1016/j.heliyon.2021.e05978",
        "tier": "tangential",
        "open_access": 1,
    },
    {
        "doi": "10.1002/maco.201307089",
        "tier": "tangential",
        "open_access": 0,
    },
    {
        "doi": "10.1155/2015/126298",
        "tier": "tangential",
        "open_access": 1,
    },
    {
        "doi": "10.1186/s13068-016-0535-9",
        "tier": "tangential",
        "open_access": 1,
    },

    # --- Patent: no DOI — seeded manually ------------------------------------
    {
        "doi": None,
        "tier": "core",
        "open_access": 1,
        "manual": {
            "title": "A kind of preparation method of seaweed-based activated carbon for supercapacitor",
            "authors": "",
            "year": 2019,
            "journal": "Google Patents",
            "abstract": (
                "Pre-treating seaweed with multivalent metal cations forms an "
                "'egg-box' coordination structure, yielding uniform mesopores "
                "that prevent capacity loss at high current densities."
            ),
        },
    },
]

# ---------------------------------------------------------------------------
# CrossRef helpers
# ---------------------------------------------------------------------------
CROSSREF_BASE = "https://api.crossref.org/works"
REQUEST_DELAY  = 1.0   # seconds between requests — polite crawling


def fetch_crossref(doi: str) -> dict | None:
    """
    Fetch metadata for a single DOI from CrossRef.
    Returns a normalised dict or None on failure.
    """
    url = f"{CROSSREF_BASE}/{doi}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [WARN] CrossRef request failed for {doi}: {exc}")
        return None

    data = response.json().get("message", {})

    title   = _extract_title(data)
    authors = _extract_authors(data)
    year    = _extract_year(data)
    journal = _extract_journal(data)
    abstract = _extract_abstract(data)

    return {
        "title":    title,
        "authors":  authors,
        "year":     year,
        "journal":  journal,
        "abstract": abstract,
    }


def _extract_title(data: dict) -> str:
    titles = data.get("title", [])
    return html.unescape(titles[0].strip()) if titles else ""


def _extract_authors(data: dict) -> str:
    authors = []
    for author in data.get("author", []):
        given  = author.get("given", "")
        family = author.get("family", "")
        full   = f"{given} {family}".strip()
        if full:
            authors.append(full)
    return ", ".join(authors)


def _extract_year(data: dict) -> int | None:
    # CrossRef stores dates in several fields; prefer published-print
    for field in ("published-print", "published-online", "created"):
        date_parts = data.get(field, {}).get("date-parts", [[]])
        if date_parts and date_parts[0]:
            return int(date_parts[0][0])
    return None


def _extract_journal(data: dict) -> str:
    container = data.get("container-title", [])
    return html.unescape(container[0].strip()) if container else ""


def _extract_abstract(data: dict) -> str:
    # CrossRef returns abstracts wrapped in JATS XML tags; strip them
    raw = data.get("abstract", "")
    cleaned = re.sub(r"<[^>]+>", "", raw).strip()
    return html.unescape(cleaned)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def ensure_schema(conn: sqlite3.Connection) -> None:
    """
    Apply schema.sql to the database if tables don't exist yet.
    Safe to call on every run — CREATE TABLE IF NOT EXISTS is idempotent.
    """
    schema_path = pathlib.Path(__file__).parent.parent / "db" / "schema.sql"
    conn.executescript(schema_path.read_text())


def insert_paper(conn: sqlite3.Connection, record: dict) -> int | None:
    """
    Insert a paper record. Skips silently on DOI collision (UNIQUE constraint).
    Returns the new rowid or None if skipped.
    """
    try:
        cursor = conn.execute(
            """
            INSERT INTO papers (title, authors, year, journal, doi, abstract,
                                tier, open_access)
            VALUES (:title, :authors, :year, :journal, :doi, :abstract,
                    :tier, :open_access)
            """,
            record,
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        print(f"  [SKIP] Already in database: {record.get('doi') or record.get('title')}")
        return None


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def build_records() -> list[dict]:
    """
    Iterate over CORPUS, call CrossRef for each DOI, and return
    a list of fully-populated records ready for insertion or display.
    """
    records = []

    for entry in CORPUS:
        doi  = entry["doi"]
        tier = entry["tier"]
        oa   = entry["open_access"]

        if doi is None:
            # Patent — use manual metadata directly
            manual = entry["manual"]
            record = {**manual, "doi": None, "tier": tier, "open_access": oa}
            print(f"  [MANUAL] {record['title'][:70]}")
            records.append(record)
            continue

        print(f"  [FETCH]  {doi}")
        metadata = fetch_crossref(doi)
        time.sleep(REQUEST_DELAY)

        if metadata is None:
            print(f"  [WARN]   Skipping {doi} — no metadata returned")
            continue

        record = {**metadata, "doi": doi, "tier": tier, "open_access": oa}
        records.append(record)

    return records


def run(db_path: str, insert: bool) -> None:
    print(f"\nBagong Enerhiya — Literature Ingestion")
    print(f"Target DB : {db_path}")
    print(f"Mode      : {'INSERT' if insert else 'DRY RUN'}")
    print("-" * 50)

    records = build_records()

    print(f"\nFetched {len(records)} / {len(CORPUS)} records")

    if not insert:
        print("\n--- Dry-run preview (first 3 records) ---")
        for rec in records[:3]:
            print(json.dumps(rec, indent=2, ensure_ascii=False))
        print("\nRe-run with --insert to write to the database.")
        return

    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    inserted = 0
    skipped  = 0

    for rec in records:
        rowid = insert_paper(conn, rec)
        if rowid:
            inserted += 1
            print(f"  [OK]     id={rowid:>3}  {rec['title'][:65]}")
        else:
            skipped += 1

    conn.close()

    print(f"\nDone. Inserted: {inserted}  Skipped: {skipped}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed bagong_enerhiya.db with corpus papers via CrossRef."
    )
    parser.add_argument(
        "--insert",
        action="store_true",
        help="Write records to the database (default: dry-run only)",
    )
    parser.add_argument(
        "--db",
        default=str(pathlib.Path(__file__).parent.parent / "db" / "bagong_enerhiya.db"),
        help="Path to the SQLite database file",
    )
    args = parser.parse_args()

    run(db_path=args.db, insert=args.insert)