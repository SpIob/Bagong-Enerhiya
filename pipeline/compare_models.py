"""
pipeline/compare_models.py
==========================
Empirically compares SciBERT and MatSciBERT as zero-shot NER pipelines
on three anchor paper abstracts pulled live from bagong_enerhiya.db.

Answers Open Question #1:
  "Which pre-trained model performs best for extracting electrochemical
   properties from materials science abstracts?"

What this script does
---------------------
1. Loads three anchor abstracts from the database (IDs 1, 2, 5 — all
   open-access core papers with rich entity content).
2. Runs each abstract through both models using HuggingFace's token-
   classification pipeline (zero-shot NER, no fine-tuning).
3. Filters predicted tokens to those overlapping with a hand-defined
   entity vocabulary — the four target property types for the pipeline:
     - specific_capacitance  (e.g. "110.8 F/g", "226.3 Fg-1")
     - BET_surface_area      (e.g. "603.7 m2/g")
     - pyrolysis_temp        (e.g. "900°C", "600–900 °C")
     - activating_agent      (e.g. "KOH", "NaCl", "ZnCl2")
4. Prints a side-by-side comparison table for each abstract.
5. Prints a summary recommendation.

Usage
-----
    python pipeline/compare_models.py
    python pipeline/compare_models.py --db path/to/other.db

Models used
-----------
- allenai/scibert_scivocab_uncased  (general scientific NER)
- m3rg-iitd/matscibert              (materials science NER)

Both are loaded from HuggingFace Hub — first run will download ~440MB
each. Subsequent runs use the local cache (~/.cache/huggingface/).

Note: This script uses CPU inference. On a MacBook it takes ~2–3 minutes
per model per abstract. Total runtime: ~15–20 minutes.
"""

import argparse
import pathlib
import re
import sqlite3
import textwrap

# HuggingFace pipeline — loaded lazily to avoid slow import on module load
from transformers import pipeline as hf_pipeline

# ---------------------------------------------------------------------------
# Anchor paper IDs to test against
# ID 1 = Yang 2022   (BET, capacitance, activation, cycling)
# ID 2 = Jiang 2021  (capacitance, pyrolysis temp, cycling)
# ID 5 = Liu 2023    (N-doped, capacitance, energy/power density)
# ---------------------------------------------------------------------------
ANCHOR_IDS = [1, 2, 5]

MODELS = {
    "SciBERT":    "allenai/scibert_scivocab_uncased",
    "MatSciBERT": "m3rg-iitd/matscibert",
}

# ---------------------------------------------------------------------------
# Lightweight keyword vocabulary for the 4 target entity types.
# We use substring matching against predicted token spans as a proxy for
# entity-type classification — good enough for a model selection decision.
# ---------------------------------------------------------------------------
ENTITY_VOCAB: dict[str, list[str]] = {
    "specific_capacitance": [
        "f/g", "fg", "f g", "mf/cm", "farad", "capacitance", "capacitor",
        "supercapacitance", "specific cap",
    ],
    "BET_surface_area": [
        "m2/g", "m²/g", "m2 g", "surface area", "bet", "sbet",
    ],
    "pyrolysis_temp": [
        "°c", "celsius", "700", "800", "900", "600", "1000",
        "carbonisation", "carbonization", "pyrolysis",
    ],
    "activating_agent": [
        "koh", "nacl", "zncl", "h3po4", "co2", "naoh", "k2co3",
        "activat", "activation agent",
    ],
}


def classify_token(token_text: str) -> str | None:
    """
    Map a token string to one of the 4 target entity types, or None.
    Case-insensitive substring match against ENTITY_VOCAB.
    """
    lower = token_text.lower()
    for entity_type, keywords in ENTITY_VOCAB.items():
        if any(kw in lower for kw in keywords):
            return entity_type
    return None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def load_abstracts(db_path: str, ids: list[int]) -> list[dict]:
    """Return id, title, abstract for the given paper IDs."""
    conn = sqlite3.connect(db_path)
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT id, title, abstract FROM papers WHERE id IN ({placeholders})",
        ids,
    ).fetchall()
    conn.close()

    results = [{"id": r[0], "title": r[1], "abstract": r[2]} for r in rows]

    # Warn if any anchor abstract is empty (paywalled papers)
    for r in results:
        if not r["abstract"]:
            print(f"  [WARN] Paper id={r['id']} has no abstract — skipping.")

    return [r for r in results if r["abstract"]]


# ---------------------------------------------------------------------------
# NER runner
# ---------------------------------------------------------------------------
def run_ner(model_name: str, text: str) -> list[dict]:
    """
    Run the HuggingFace token-classification pipeline on text.
    Returns a list of {word, score, entity_type} dicts for tokens
    that match the entity vocabulary.
    """
    ner = hf_pipeline(
        "token-classification",
        model=model_name,
        aggregation_strategy="simple",   # merges subword tokens into words
        device=-1,                        # CPU
    )
    raw_entities = ner(text)

    matched = []
    for ent in raw_entities:
        word = ent.get("word", "")
        score = round(ent.get("score", 0.0), 3)
        entity_type = classify_token(word)
        if entity_type:
            matched.append({
                "word":        word,
                "score":       score,
                "entity_type": entity_type,
                "label":       ent.get("entity_group", ent.get("entity", "")),
            })

    return matched


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------
SEPARATOR = "─" * 72

def print_header(title: str) -> None:
    print(f"\n{SEPARATOR}")
    wrapped = textwrap.fill(title, width=70)
    print(wrapped)
    print(SEPARATOR)


def print_model_results(model_name: str, entities: list[dict]) -> None:
    print(f"\n  ── {model_name} ──")
    if not entities:
        print("    (no entity-vocabulary matches found)")
        return
    for e in entities:
        print(
            f"    [{e['entity_type']:22}]  "
            f"{e['word']:30}  score={e['score']:.3f}  label={e['label']}"
        )


def print_summary(scores: dict[str, dict[str, int]]) -> None:
    """
    scores = { model_name: { entity_type: hit_count, ... } }
    Prints a summary table and a plain-language recommendation.
    """
    print(f"\n{'='*72}")
    print("SUMMARY — Entity hit counts across all 3 abstracts")
    print(f"{'='*72}")

    entity_types = list(ENTITY_VOCAB.keys())
    col_w = 24

    # Header row
    header = f"  {'Entity type':<{col_w}}"
    for model_name in scores:
        header += f"  {model_name:>12}"
    print(header)
    print("  " + "─" * (col_w + 16 * len(scores)))

    # Data rows
    totals = {m: 0 for m in scores}
    for et in entity_types:
        row = f"  {et:<{col_w}}"
        for model_name, counts in scores.items():
            count = counts.get(et, 0)
            totals[model_name] += count
            row += f"  {count:>12}"
        print(row)

    # Totals
    print("  " + "─" * (col_w + 16 * len(scores)))
    total_row = f"  {'TOTAL':<{col_w}}"
    for model_name in scores:
        total_row += f"  {totals[model_name]:>12}"
    print(total_row)

    # Recommendation
    winner = max(totals, key=lambda m: totals[m])
    loser  = min(totals, key=lambda m: totals[m])
    print(f"\n{'='*72}")
    print("RECOMMENDATION")
    print(f"{'='*72}")
    print(f"  {winner} matched more entity-vocabulary tokens ({totals[winner]}) "
          f"than {loser} ({totals[loser]}).")
    print(f"  → Use {winner} as the NER backbone for pipeline/extract.py")
    print()
    print("  Note: This is a zero-shot proxy test, not a precision/recall eval.")
    print("  The model that finds more relevant tokens here is the better starting")
    print("  point. Final accuracy will be measured in Week 4 against hand labels.")
    print(f"{'='*72}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run(db_path: str) -> None:
    print("\nBagong Enerhiya — NLP Model Comparison")
    print(f"Database  : {db_path}")
    print(f"Models    : {', '.join(MODELS.keys())}")
    print(f"Abstracts : paper ids {ANCHOR_IDS}")
    print(SEPARATOR)

    papers = load_abstracts(db_path, ANCHOR_IDS)
    if not papers:
        print("No abstracts found. Check that --insert was run first.")
        return

    # scores[model_name][entity_type] = total hit count across all abstracts
    scores: dict[str, dict[str, int]] = {m: {} for m in MODELS}

    for paper in papers:
        print_header(f"Paper id={paper['id']}: {paper['title']}")
        # Truncate very long abstracts to 512 tokens (model max)
        abstract = paper["abstract"][:1800]

        for model_label, model_name in MODELS.items():
            print(f"\n  Loading {model_label} ({model_name})...")
            try:
                entities = run_ner(model_name, abstract)
            except Exception as exc:
                print(f"  [ERROR] {model_label} failed: {exc}")
                entities = []

            print_model_results(model_label, entities)

            # Accumulate scores
            for e in entities:
                et = e["entity_type"]
                scores[model_label][et] = scores[model_label].get(et, 0) + 1

    print_summary(scores)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare SciBERT vs MatSciBERT on anchor paper abstracts."
    )
    parser.add_argument(
        "--db",
        default=str(pathlib.Path(__file__).parent.parent / "db" / "bagong_enerhiya.db"),
        help="Path to the SQLite database file",
    )
    args = parser.parse_args()
    run(db_path=args.db)