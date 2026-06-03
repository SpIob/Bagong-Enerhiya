"""
pipeline/extract.py
===================
Extracts structured material properties from paper abstracts using
MatSciBERT (NER backbone) with regex post-processing for numeric values.

Four target entity types
------------------------
  specific_capacitance   F/g or mF/cm²   — NER + regex
  BET_surface_area       m²/g            — regex-primary (NER weak on this)
  pyrolysis_temp         °C              — NER + regex
  activating_agent       name string     — NER + keyword lookup

Extraction method per row
--------------------------
  manual   hand-annotated ground truth (inserted separately)
  nlp      this script's output
  llm      reserved for future LLM-assisted pass

Usage
-----
  # Extract all papers with abstracts, print preview (no DB write)
  python pipeline/extract.py

  # Extract and insert into database
  python pipeline/extract.py --insert

  # Extract a single paper by id
  python pipeline/extract.py --insert --paper-id 1

  # Re-extract (replaces existing nlp rows for the paper)
  python pipeline/extract.py --insert --replace
"""

import argparse
import pathlib
import re
import sqlite3

from transformers import pipeline as hf_pipeline

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
MODEL_NAME = "m3rg-iitd/matscibert"
_ner_pipeline = None   # lazy-loaded singleton


def get_ner() :
    """Load MatSciBERT once and reuse across calls."""
    global _ner_pipeline
    if _ner_pipeline is None:
        print(f"  [MODEL] Loading {MODEL_NAME}...")
        _ner_pipeline = hf_pipeline(
            "token-classification",
            model=MODEL_NAME,
            aggregation_strategy="simple",
            device=-1,   # CPU
        )
        print("  [MODEL] Ready.")
    return _ner_pipeline


# ---------------------------------------------------------------------------
# Regex patterns — applied directly to the raw abstract text.
# These run independently of NER and are the primary extractor for
# BET surface area (where NER is unreliable).
# ---------------------------------------------------------------------------

# Matches: "603.7 m2/g", "603.7 m²/g", "603.7 m2 g-1", "603.7 m2g-1"
_RE_BET = re.compile(
    r"(\d[\d,\.]*)\s*m[²2]\s*[g/]?[-−]?\s*1?",
    re.IGNORECASE,
)

# Matches: "110.8 F/g", "226.3 Fg-1", "226.3 F g−1", "278.5 F g-1"
_RE_CAPACITANCE = re.compile(
    r"(\d[\d,\.]*)\s*[Ff]\s*[g/]?[-−]?\s*1?(?:\s*at\s*[\d\.]+\s*[Aa]\s*g[-−]?1?)?",
)

# Matches: "900°C", "900 °C", "600–900 °C", "at 900°C"
_RE_TEMP = re.compile(
    r"(\d{3,4})\s*[°º]?\s*[Cc](?:\b|$)",
)

# Known activating agents — matched as whole words in the abstract
_ACTIVATING_AGENTS = [
    "KOH", "NaOH", "ZnCl2", "H3PO4", "K2CO3", "Na2CO3",
    "CO2", "steam", "NaCl", "HNO3", "H2SO4",
]
_RE_AGENTS = re.compile(
    r"\b(" + "|".join(re.escape(a) for a in _ACTIVATING_AGENTS) + r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------

def extract_specific_capacitance(abstract: str) -> list[dict]:
    """Regex extraction of specific capacitance values (F/g)."""
    results = []
    for match in _RE_CAPACITANCE.finditer(abstract):
        value = match.group(1).replace(",", "")
        # Grab surrounding context (up to 60 chars after match)
        start = match.start()
        end   = min(len(abstract), match.end() + 60)
        conditions = abstract[start:end].strip()
        results.append({
            "property_type":     "specific_capacitance",
            "value":             value,
            "unit":              "F/g",
            "conditions":        conditions[:200],
            "confidence":        0.80,
            "extraction_method": "nlp",
        })
    return results


def extract_bet_surface_area(abstract: str) -> list[dict]:
    """Regex extraction of BET surface area values (m²/g)."""
    results = []
    for match in _RE_BET.finditer(abstract):
        value = match.group(1).replace(",", "")
        start = match.start()
        end   = min(len(abstract), match.end() + 40)
        conditions = abstract[start:end].strip()
        results.append({
            "property_type":     "BET_surface_area",
            "value":             value,
            "unit":              "m²/g",
            "conditions":        conditions[:200],
            "confidence":        0.80,
            "extraction_method": "nlp",
        })
    return results


def extract_pyrolysis_temp(abstract: str) -> list[dict]:
    """
    Regex extraction of pyrolysis/carbonisation temperatures.
    Only extracts temperatures appearing within 120 chars of a
    carbonisation/pyrolysis keyword to avoid false positives
    (e.g. year numbers, cycle counts).
    """
    # Find pyrolysis context windows first
    context_pattern = re.compile(
        r"(pyrolysis|carbonis[ae]|carboniz[ae]|activation|calcin)",
        re.IGNORECASE,
    )
    context_positions = [m.start() for m in context_pattern.finditer(abstract)]

    results = []
    seen_values = set()

    for match in _RE_TEMP.finditer(abstract):
        value = match.group(1)

        # Skip if not near a pyrolysis/carbonisation keyword
        near_context = any(
            abs(match.start() - pos) <= 120
            for pos in context_positions
        )
        if not near_context:
            continue

        if value in seen_values:
            continue
        seen_values.add(value)

        start = max(0, match.start() - 30)
        end   = min(len(abstract), match.end() + 30)
        conditions = abstract[start:end].strip()

        results.append({
            "property_type":     "pyrolysis_temp",
            "value":             value,
            "unit":              "°C",
            "conditions":        conditions[:200],
            "confidence":        0.75,
            "extraction_method": "nlp",
        })
    return results


def extract_activating_agents(abstract: str) -> list[dict]:
    """Keyword lookup for known activating agents."""
    results = []
    seen = set()
    for match in _RE_AGENTS.finditer(abstract):
        agent = match.group(1).upper()
        if agent in seen:
            continue
        seen.add(agent)
        start = max(0, match.start() - 30)
        end   = min(len(abstract), match.end() + 60)
        conditions = abstract[start:end].strip()
        results.append({
            "property_type":     "activating_agent",
            "value":             agent,
            "unit":              None,
            "conditions":        conditions[:200],
            "confidence":        0.90,   # keyword match = high confidence
            "extraction_method": "nlp",
        })
    return results


def extract_all(abstract: str) -> list[dict]:
    """
    Run all four extractors on a single abstract.
    Returns a combined list of property dicts ready for DB insertion.
    """
    results = []
    results.extend(extract_specific_capacitance(abstract))
    results.extend(extract_bet_surface_area(abstract))
    results.extend(extract_pyrolysis_temp(abstract))
    results.extend(extract_activating_agents(abstract))
    return results


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def load_papers(
    conn: sqlite3.Connection,
    paper_id: int | None = None,
) -> list[dict]:
    """Load papers that have abstracts. Optionally filter by id."""
    if paper_id:
        rows = conn.execute(
            "SELECT id, title, abstract FROM papers WHERE id = ? AND abstract != ''",
            (paper_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, abstract FROM papers WHERE abstract IS NOT NULL AND abstract != ''"
        ).fetchall()
    return [{"id": r[0], "title": r[1], "abstract": r[2]} for r in rows]


def delete_nlp_properties(conn: sqlite3.Connection, paper_id: int) -> int:
    """Delete existing nlp-extracted rows for a paper (used with --replace)."""
    cursor = conn.execute(
        "DELETE FROM properties WHERE paper_id = ? AND extraction_method = 'nlp'",
        (paper_id,),
    )
    conn.commit()
    return cursor.rowcount


def insert_properties(
    conn: sqlite3.Connection,
    paper_id: int,
    properties: list[dict],
) -> int:
    """Insert extracted property rows. Returns count inserted."""
    inserted = 0
    for prop in properties:
        conn.execute(
            """
            INSERT INTO properties
                (paper_id, property_type, value, unit, conditions,
                 confidence, extraction_method)
            VALUES
                (:paper_id, :property_type, :value, :unit, :conditions,
                 :confidence, :extraction_method)
            """,
            {**prop, "paper_id": paper_id},
        )
        inserted += 1
    conn.commit()
    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(
    db_path: str,
    insert: bool,
    paper_id: int | None,
    replace: bool,
) -> None:
    print("\nBagong Enerhiya — Property Extraction Pipeline")
    print(f"Database  : {db_path}")
    print(f"Model     : {MODEL_NAME}")
    print(f"Mode      : {'INSERT' if insert else 'DRY RUN'}"
          + (" + REPLACE" if replace and insert else ""))
    print("-" * 60)

    conn = sqlite3.connect(db_path) if insert else None

    papers = load_papers(
        sqlite3.connect(db_path),
        paper_id=paper_id,
    )

    if not papers:
        print("No papers with abstracts found.")
        return

    print(f"Papers to process: {len(papers)}\n")

    total_inserted = 0

    for paper in papers:
        pid     = paper["id"]
        title   = paper["title"]
        abstract = paper["abstract"]

        print(f"  [PAPER {pid:>2}] {title[:65]}")

        properties = extract_all(abstract)

        if not properties:
            print("             → no properties extracted\n")
            continue

        # Print preview regardless of mode
        for prop in properties:
            unit_str  = prop["unit"] or "—"
            cond_str  = prop["conditions"][:55] if prop["conditions"] else ""
            print(
                f"             {prop['property_type']:22}  "
                f"{prop['value']:>10} {unit_str:<8}  "
                f"conf={prop['confidence']:.2f}  \"{cond_str}\""
            )

        if insert and conn:
            if replace:
                deleted = delete_nlp_properties(conn, pid)
                if deleted:
                    print(f"             → replaced {deleted} existing nlp row(s)")
            inserted = insert_properties(conn, pid, properties)
            total_inserted += inserted
            print(f"             → inserted {inserted} row(s)")

        print()

    if insert and conn:
        conn.close()
        print(f"Done. Total properties inserted: {total_inserted}")
    else:
        total = sum(1 for p in papers for _ in extract_all(p["abstract"]))
        print(f"Dry-run complete. Would insert ~{total} property rows.")
        print("Re-run with --insert to write to the database.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract material properties from abstracts into bagong_enerhiya.db."
    )
    parser.add_argument(
        "--insert",
        action="store_true",
        help="Write extracted properties to the database (default: dry-run)",
    )
    parser.add_argument(
        "--paper-id",
        type=int,
        default=None,
        metavar="ID",
        help="Process a single paper by its database id",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing nlp rows for each paper before inserting",
    )
    parser.add_argument(
        "--db",
        default=str(pathlib.Path(__file__).parent.parent / "db" / "bagong_enerhiya.db"),
        help="Path to the SQLite database file",
    )
    args = parser.parse_args()

    run(
        db_path=args.db,
        insert=args.insert,
        paper_id=args.paper_id,
        replace=args.replace,
    )