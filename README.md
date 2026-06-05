# ⚗️ Bagong Enerhiya

> **AI-assisted literature intelligence for Philippine macroalgae supercapacitor materials research**

Bagong Enerhiya is an open-source research tool that ingests scientific literature, extracts structured material properties using a domain-adapted NLP pipeline, and surfaces the result through an interactive web interface — built to document and quantify a specific research gap: **zero published studies exist on *Eucheuma cottonii* or *Kappaphycus alvarezii* as supercapacitor electrode materials**, despite the Philippines being the world's foremost producer of both species.

Built in three days as a solo student project. Zero budget. Fully reproducible.

---

## The Research Gap

The Philippines produces over 1.5 million metric tons of macroalgae annually — primarily *Eucheuma cottonii* and *Kappaphycus alvarezii* for carrageenan extraction. The post-extraction solid residue is discarded as waste.

Related seaweed species (Sargassum, Ulva, Gracilaria) have yielded supercapacitor electrodes with specific capacitances of **45.9–354 F/g**. Philippine commercial species: **0 papers**.

Bagong Enerhiya makes this gap programmatically visible and provides the supporting literature context needed to design the first experimental investigation.

---

## What It Does

```
Semantic Scholar API ─┐
CrossRef API          ├──► ingest ──► SQLite DB ──► FastAPI ──► Streamlit UI
arXiv API             ┘               (papers,       3 REST    3 views:
                                       properties)   endpoints  Browser · Detail · Compare
```

**Literature ingestion** — fetches and deduplicates papers by DOI from CrossRef and by keyword from Semantic Scholar. Handles HTML entity decoding, tier classification (core / supporting / tangential), and schema auto-initialisation on first run.

**Property extraction** — a hybrid MatSciBERT + regex pipeline extracts four entity types from paper abstracts: specific capacitance (F/g), BET surface area (m²/g), pyrolysis temperature (°C), and activating agent. Confidence scores and test conditions are stored alongside each extracted value.

**FastAPI backend** — three endpoints expose the corpus as a public API: `GET /papers`, `GET /papers/{id}`, `GET /properties`. Full filtering, pagination, and Swagger docs at `/docs`.

**Streamlit interface** — Paper Browser (search + filter), Paper Detail (abstract + properties table), and Properties Comparison (ranked bar chart + cross-paper table with research gap callout).

---

## Corpus

| Stat | Value |
|---|---|
| Total papers | 62 |
| Core (seaweed electrode) | 25 |
| Supporting | 30 |
| Tangential | 7 |
| Year range | 2009–2026 |
| Open access | 18 (29%) |
| Philippine-species electrode papers | **0** |

Capacitance range across core seaweed papers: **45.9–354 F/g** (Gracilaria spinulosa → Sargassum Wightii).

---

## NLP Pipeline

MatSciBERT (`m3rg-iitd/matscibert`) was selected over SciBERT after empirical comparison on three anchor paper abstracts. MatSciBERT wins on span coherence (groups numeric value + unit together), activating agent recall, and pyrolysis temperature grouping. BET surface area uses regex-primary extraction due to model weakness on that entity type.

| Property | Method | Unit | Confidence |
|---|---|---|---|
| `specific_capacitance` | Regex | F/g | 0.80 |
| `BET_surface_area` | Regex | m²/g | 0.80 |
| `pyrolysis_temp` | Regex + context window | °C | 0.75 |
| `activating_agent` | Keyword lookup | — | 0.90 |

---

## Tech Stack

| Layer | Tool | Notes |
|---|---|---|
| Frontend | Streamlit | Foundry dark theme — `#121212` / `#ff4d00` / JetBrains Mono |
| Backend | FastAPI + Uvicorn | 3 endpoints, CORS-enabled, Swagger at `/docs` |
| Database | SQLite | `db/bagong_enerhiya.db` — `papers` + `properties` tables |
| NLP | MatSciBERT (HuggingFace) | Zero-shot token classification, CPU inference |
| Literature | Semantic Scholar API | Key required — 100 req/5 min |
| Metadata | CrossRef API | No key — unlimited |
| Version control | GitHub | This repo |

---

## Installation

### Prerequisites

- Python 3.10+
- A Semantic Scholar API key → [api.semanticscholar.org](https://api.semanticscholar.org)

### Setup

```bash
# 1. Clone
git clone https://github.com/SpIob/Bagong-Enerhiya.git
cd Bagong-Enerhiya

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Semantic Scholar API key
echo "semantic_scholar=your_key_here" > apis.txt
# apis.txt is .gitignored — never committed
```

### Initialise the database

```bash
python3 -c "
import sqlite3, pathlib
conn = sqlite3.connect('db/bagong_enerhiya.db')
conn.executescript(pathlib.Path('db/schema.sql').read_text())
conn.close()
print('Database initialised.')
"
```

### Build the corpus

```bash
# Seed from the 14 hand-curated papers (CrossRef)
python ingest/fetch_papers.py --insert

# Expand via Semantic Scholar keyword search
python ingest/search_papers.py --insert

# Extract material properties from all abstracts
python pipeline/extract.py --insert
```

### Run

Open two terminals from the project root:

```bash
# Terminal 1 — FastAPI backend
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Streamlit frontend
streamlit run app/streamlit_app.py
```

Open `http://localhost:8501` in your browser.
API docs at `http://localhost:8000/docs`.

---

## Project Structure

```
Bagong Enerhiya/
├── .streamlit/
│   └── config.toml          # Foundry dark theme
├── api/
│   └── main.py              # FastAPI — GET /papers, /papers/{id}, /properties
├── app/
│   └── streamlit_app.py     # Streamlit — Paper Browser, Detail, Properties
├── db/
│   ├── schema.sql           # papers + properties tables, indexes, constraints
│   └── bagong_enerhiya.db   # SQLite corpus database (auto-generated)
├── ingest/
│   ├── fetch_papers.py      # Seed corpus from CrossRef by DOI
│   ├── search_papers.py     # Expand corpus via Semantic Scholar keywords
│   └── clean_titles.py      # Strip HTML tags from CrossRef title data
├── pipeline/
│   ├── compare_models.py    # SciBERT vs MatSciBERT evaluation script
│   └── extract.py           # MatSciBERT + regex property extraction
├── writeup/
│   └── paper.md             # Technical write-up (full paper draft)
├── apis.txt                 # API keys — NOT committed (.gitignored)
├── requirements.txt
└── README.md
```

---

## API Reference

The FastAPI backend is also a public data API. All endpoints return paginated JSON.

### `GET /papers`
```
?tier=core|supporting|tangential
&year_from=2009
&year_to=2026
&open_access=true|false
&keyword=sargassum
&limit=50
&offset=0
```

### `GET /papers/{id}`
Returns full paper metadata including all extracted properties.

### `GET /properties`
```
?property_type=specific_capacitance|BET_surface_area|pyrolysis_temp|activating_agent
&tier=core
&min_confidence=0.7
&extraction_method=manual|nlp|llm
&limit=100
```

Interactive docs: `http://localhost:8000/docs`

---

## Initial Roadmap

- [x] Week 1 — Corpus scoping, inclusion criteria, GitHub setup
- [x] Week 2 — Ingestion pipeline, SQLite schema, MatSciBERT extraction
- [x] Week 3 — FastAPI backend, Streamlit UI, end-to-end demo
- [x] Week 4 — Write-up, README, final commit
- [ ] Fine-tune MatSciBERT on hand-annotated seaweed electrode abstracts
- [ ] Add cycling stability and heteroatom content extraction
- [ ] First experimental synthesis of *K. alvarezii*-derived activated carbon
- [ ] Expand to other Philippine resources (nickel laterite, coconut shell, bamboo)

---

## Contributing

Contributions are welcome, especially:
- Hand-annotated property corrections (add `extraction_method = 'manual'` rows)
- New paper additions to the corpus via pull request
- Extraction pipeline improvements for BET surface area precision

Please open an issue before submitting a pull request for significant changes.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Author

**Jan Mico M. Arenga**
Incoming BS AI Engineering Student, Mapúa University, Manila, Philippines
[GitHub](https://github.com/SpIob)

*Bagong Enerhiya* (Filipino: "New Energy") is an independent student research initiative exploring the untapped electrochemical potential of Philippine-farmed macroalgae — and the infrastructure needed to find it.
