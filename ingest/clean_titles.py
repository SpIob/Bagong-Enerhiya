"""
ingest/clean_titles.py
======================
One-time cleanup: strips residual HTML tags (e.g. <i>, </i>) from paper
titles that CrossRef returned with inline markup.

Affected rows (as of initial insert):
  id=11  Kappaphycus alvarezii – A marine red alga ...   (<i> tags)
  id=12  Heavy Metal Adsorption onto Kappaphycus sp. ... (<i> tags)

Safe to re-run — uses a regex UPDATE that is idempotent once tags are gone.

Usage
-----
    python ingest/clean_titles.py
    python ingest/clean_titles.py --db path/to/other.db
"""

import argparse
import pathlib
import re
import sqlite3


def strip_html_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def clean_titles(db_path: str) -> None:
    conn = sqlite3.connect(db_path)

    rows = conn.execute("SELECT id, title FROM papers").fetchall()
    updated = 0

    for paper_id, title in rows:
        cleaned = strip_html_tags(title)
        if cleaned != title:
            conn.execute(
                "UPDATE papers SET title = ?, updated_at = datetime('now') WHERE id = ?",
                (cleaned, paper_id),
            )
            print(f"  [FIXED] id={paper_id:>3}  {cleaned[:70]}")
            updated += 1

    conn.commit()
    conn.close()
    print(f"\nDone. {updated} title(s) cleaned.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Strip HTML tags from paper titles in bagong_enerhiya.db."
    )
    parser.add_argument(
        "--db",
        default=str(pathlib.Path(__file__).parent.parent / "db" / "bagong_enerhiya.db"),
        help="Path to the SQLite database file",
    )
    args = parser.parse_args()
    clean_titles(db_path=args.db)