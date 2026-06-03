# ⚗️ Bagong Enerhiya

> **AI-powered literature intelligence for Philippine natural resource-based energy materials**

Bagong Enerhiya is an open-source, AI-assisted literature intelligence tool that curates, organizes, and surfaces insights from existing scientific literature on Philippine-derived energy materials — giving Filipino researchers a focused starting point for computational chemistry and renewable energy materials discovery.

---

## 🔬 Anchor Research Question

> *Which Philippine seaweed (macroalgae) shows promise as a supercapacitor electrode material, and what properties make it viable or limiting?*

The project focuses on *Eucheuma cottonii* and *Kappaphycus alvarezii* — the Philippines is the world's top producer of both species — and investigates their potential as biochar-derived supercapacitor electrode materials. Fewer than 50 papers globally cover seaweed biochar for electrochemical devices, and **zero** are Philippines-specific, making this a high-novelty research gap.

---

## 🚀 Features

- **Literature ingestion pipeline** — fetches papers from Semantic Scholar, CrossRef, and arXiv APIs
- **AI-assisted extraction** — uses SciBERT / MatSciBERT (HuggingFace Transformers) for named entity recognition of material properties (BET surface area, specific capacitance, heteroatom doping, cycling stability, etc.)
- **SQLite database** — stores and indexes literature metadata and extracted properties
- **FastAPI backend** — exposes data processing endpoints for the frontend
- **Streamlit dashboard** — interactive search, filter, annotation, extracted property tables, and performance plots

---

## 🛠️ Technical Stack

| Component | Tool / Library | Purpose |
|---|---|---|
| Frontend | Streamlit | Interactive user interface |
| Backend API | FastAPI + Uvicorn | Data processing and logic |
| Database | SQLite (local) → Turso (cloud, optional) | Store literature metadata and extracted properties |
| NLP / AI | HuggingFace Transformers (SciBERT / MatSciBERT) | Abstract parsing, entity extraction, summarization |
| Literature API | Semantic Scholar API | Fetch papers from academic databases |
| Supplementary APIs | CrossRef API, arXiv API | Metadata and preprint access |
| Hosting | HuggingFace Spaces or Railway | Deploy the application |
| Version Control | GitHub | Code and project tracking |

---

## 📦 Installation

### Prerequisites

- Python 3.10+
- `pip` or `conda`
- A Semantic Scholar API key ([api.semanticscholar.org](https://api.semanticscholar.org))
- A HuggingFace access token ([huggingface.co](https://huggingface.co)) *(for gated models, if needed)*

### Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/<your-username>/bagong-enerhiya.git
   cd bagong-enerhiya
   ```

2. **Create and activate a virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**

   Create a `.env` file in the project root:

   ```env
   SEMANTIC_SCHOLAR_API_KEY=your_key_here
   HUGGINGFACE_TOKEN=your_token_here
   ```

5. **Run the backend**

   ```bash
   uvicorn app.main:app --reload
   ```

6. **Run the frontend**

   ```bash
   streamlit run frontend/app.py
   ```

---

## 🗂️ Project Structure

```
bagong-enerhiya/
├── app/
│   ├── main.py            # FastAPI app entry point
│   ├── routes/            # API route definitions
│   ├── models/            # SQLAlchemy database models
│   └── pipeline/          # Literature ingestion and NLP pipeline
├── frontend/
│   └── app.py             # Streamlit dashboard
├── data/
│   └── literature.db      # SQLite database (auto-generated)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 📅 4-Week Roadmap

| Week | Phase | Key Tasks |
|---|---|---|
| 1 | **Scope & Data** | Define search queries and inclusion criteria; source papers via APIs; set up GitHub repo and Python environment |
| 2 | **Pipeline** | Build literature ingestion pipeline; extract material properties using open LLM APIs; design and populate SQLite schema |
| 3 | **Interface** | Build Streamlit UI; connect FastAPI backend; integrate entity extraction; display interactive tables and plots |
| 4 | **Write-up & Polish** | Verify extraction accuracy on test papers; write README and user guide; draft technical write-up; record demo; publish repo |

---

## 🧪 NLP Extraction Targets

Properties targeted for extraction from paper abstracts:

- Porosity and specific surface area (BET)
- Heteroatom doping (N, O)
- Carbon yield after pyrolysis/activation
- Electrochemical capacitance (CV, GCD)
- Cycling stability
- Conductivity
- Synthesis temperature and activating agent
- Energy and power density

**First-iteration performance targets:** Precision ≥ 0.70 · Recall ≥ 0.60 · F1 ≥ 0.65

---

## 📚 Literature APIs

| API | Access | Free Tier |
|---|---|---|
| Semantic Scholar | API key required | 100 req / 5 min |
| CrossRef | No key needed | Unlimited |
| arXiv | No key needed | Unlimited |
| HuggingFace Models Hub | Access token | Free for inference |
| Materials Project | API key required | Free |

---

## ❓ Open Questions

- Which pre-trained model performs best for extracting electrochemical properties from materials science abstracts — SciBERT, MatSciBERT, or a general-purpose LLM like Mistral 7B?
- How should papers behind paywalls be handled — rely on open-access preprints only, or include metadata without full text?
- Is there an existing open dataset of seaweed carbon properties (not PH-specific) that can bootstrap the initial corpus?
- Can synthesis conditions be extracted reliably from abstracts, or does this require full-text access?
- What is the best way to normalize performance comparisons across studies using different testing conditions?
- Should a manual annotation correction step be built in, and how will extraction accuracy be measured?
- What open-source license (MIT or Apache 2.0) is most appropriate?

---

## 📄 License

This project is a student initiative. License TBD (MIT or Apache 2.0 — see Open Questions above).

---

## 🙏 Acknowledgements

This project is part of ongoing research into renewable energy materials from Philippine natural resources, with a focus on the untapped electrochemical potential of locally farmed macroalgae species (*Eucheuma cottonii* and *Kappaphycus alvarezii*).
