"""
app/streamlit_app.py
====================
Streamlit frontend for Bagong Enerhiya.
Design: Foundry dark theme — #121212 background, #ff4d00 orange accent,
JetBrains Mono monospace, hairline #3a3a3a borders.

Three views:
  1. Paper Browser  — searchable, filterable corpus list
  2. Paper Detail   — full metadata + extracted properties for one paper
  3. Properties     — cross-paper comparison table and bar chart

Requires the FastAPI backend:
    uvicorn api.main:app --reload --port 8000

Run:
    streamlit run app/streamlit_app.py
"""

import re

import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE    = "http://localhost:8000"
GITHUB_URL  = "https://github.com/SpIob/Bagong-Enerhiya"

TIER_COLOURS = {
    "core":       "🟢",
    "supporting": "🟡",
    "tangential": "🔴",
}

PROPERTY_LABELS = {
    "specific_capacitance": "Specific Capacitance (F/g)",
    "BET_surface_area":     "BET Surface Area (m²/g)",
    "pyrolysis_temp":       "Pyrolysis Temperature (°C)",
    "activating_agent":     "Activating Agent",
    "heteroatom_content":   "Heteroatom Content (%)",
    "cycling_stability":    "Cycling Stability (% retention)",
    "energy_density":       "Energy Density (Wh/kg)",
    "power_density":        "Power Density (W/kg)",
}

st.set_page_config(
    page_title="Bagong Enerhiya",
    page_icon="⚗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global CSS — Foundry design system
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

/* Base */
html, body, [class*="css"] {
    font-family: 'JetBrains Mono', ui-monospace, monospace !important;
    background-color: #121212 !important;
    color: #efefef !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* Hide sidebar collapse button and its tooltip text */
[data-testid="stSidebarCollapseButton"] { display: none !important; }
button[kind="header"] { display: none !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #121212 !important;
    border-right: 1px solid #3a3a3a !important;
}
[data-testid="stSidebar"] * {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}

/* Page headings */
h1 { 
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 22px !important;
    font-weight: 700 !important;
    letter-spacing: 0.4px !important;
    text-transform: uppercase !important;
    color: #efefef !important;
    border-bottom: 1px solid #3a3a3a;
    padding-bottom: 12px;
    margin-bottom: 8px !important;
}
h2, h3 {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: 0.6px !important;
    text-transform: uppercase !important;
    color: #747474 !important;
}

/* Filter row — label style for all input widgets */
[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stNumberInput"] label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 400 !important;
    letter-spacing: 0.4px !important;
    text-transform: uppercase !important;
    color: #747474 !important;
}

/* Inputs */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background-color: #1a1a1a !important;
    border: 1px solid #3a3a3a !important;
    border-radius: 2.8px !important;
    color: #efefef !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #ff4d00 !important;
    box-shadow: 0 0 0 1px #ff4d00 !important;
}

/* Selectbox */
[data-testid="stSelectbox"] > div > div {
    background-color: #1a1a1a !important;
    border: 1px solid #3a3a3a !important;
    border-radius: 2.8px !important;
    color: #efefef !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}

/* Expanders — paper cards */
[data-testid="stExpander"] {
    background-color: #1a1a1a !important;
    border: 1px solid #3a3a3a !important;
    border-radius: 2.8px !important;
    margin-bottom: 4px !important;
}
[data-testid="stExpander"]:hover {
    border-color: #ff4d00 !important;
}
[data-testid="stExpander"] summary {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
    color: #efefef !important;
}

/* Buttons */
[data-testid="stButton"] button {
    background-color: transparent !important;
    border: 1px solid #ff4d00 !important;
    border-radius: 2.8px !important;
    color: #efefef !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
    letter-spacing: 0.4px !important;
    padding: 2px 12px !important;
    transition: border-color 0.15s, color 0.15s !important;
}
[data-testid="stButton"] button:hover {
    border-color: #efefef !important;
    color: #ff4d00 !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid #3a3a3a !important;
    border-radius: 2.8px !important;
}

/* Info / warning boxes */
[data-testid="stInfo"] {
    background-color: #1a1a1a !important;
    border-left: 3px solid #ff4d00 !important;
    border-radius: 2.8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
}

/* Divider */
hr {
    border-color: #3a3a3a !important;
}

/* Caption / muted text */
[data-testid="stCaptionContainer"] p,
.stCaption {
    color: #747474 !important;
    font-size: 12px !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* Radio nav buttons in sidebar */
[data-testid="stRadio"] label {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
    letter-spacing: 0.1px !important;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_papers(
    tier: str | None,
    year_from: int | None,
    year_to: int | None,
    open_access: bool | None,
    keyword: str | None,
    limit: int = 200,
) -> dict:
    params: dict = {"limit": limit}
    if tier:           params["tier"]        = tier
    if year_from:      params["year_from"]   = year_from
    if year_to:        params["year_to"]     = year_to
    if open_access is not None:
        params["open_access"] = str(open_access).lower()
    if keyword:        params["keyword"]     = keyword
    try:
        r = requests.get(f"{API_BASE}/papers", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        st.error(f"API error: {exc}. Is the FastAPI server running on port 8000?")
        return {"total": 0, "results": []}


@st.cache_data(ttl=60)
def fetch_paper(paper_id: int) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/papers/{paper_id}", timeout=10)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        st.error(f"API error: {exc}")
        return None


@st.cache_data(ttl=60)
def fetch_properties(
    property_type: str | None,
    tier: str | None,
    min_confidence: float,
    limit: int = 500,
) -> dict:
    params: dict = {"limit": limit, "min_confidence": min_confidence}
    if property_type: params["property_type"] = property_type
    if tier:          params["tier"]           = tier
    try:
        r = requests.get(f"{API_BASE}/properties", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        st.error(f"API error: {exc}")
        return {"total": 0, "results": []}


def clean_conditions(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        "<p style='font-size:18px;font-weight:700;letter-spacing:0.4px;"
        "text-transform:uppercase;color:#efefef;margin-bottom:2px;'>"
        "⚗️ BAGONG ENERHIYA</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='font-size:11px;color:#747474;line-height:1.5;"
        "margin-top:0;'>AI-assisted literature intelligence for<br>"
        "Philippine macroalgae supercapacitor<br>materials research.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<hr style='border-color:#3a3a3a;margin:12px 0;'/>",
        unsafe_allow_html=True,
    )

    view = st.radio(
        "Navigate",
        options=["📄  PAPER BROWSER", "🔬  PAPER DETAIL", "📊  PROPERTIES"],
        index=["📄  PAPER BROWSER", "🔬  PAPER DETAIL", "📊  PROPERTIES"].index(
            st.session_state.get("nav_override", "📄  PAPER BROWSER")
        ),
        label_visibility="collapsed",
    )
    # Clear override after it has been consumed by the radio widget
    if "nav_override" in st.session_state:
        del st.session_state["nav_override"]

    st.markdown(
        "<hr style='border-color:#3a3a3a;margin:12px 0;'/>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='font-size:11px;color:#747474;line-height:1.6;'>"
        f"Data: Semantic Scholar + CrossRef.<br>"
        f"Extraction: MatSciBERT + regex.<br>"
        f"<a href='{GITHUB_URL}' target='_blank' "
        f"style='color:#ff4d00;text-decoration:none;'>→ GitHub</a></p>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# View 1 — Paper Browser
# ---------------------------------------------------------------------------
if view == "📄  PAPER BROWSER":
    st.title("Paper Browser")
    st.caption(
        "🟢 Core — seaweed electrode papers  "
        "🟡 Supporting — adjacent methods  "
        "🔴 Tangential"
    )

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        keyword = st.text_input(
            "Search title / abstract",
            placeholder="e.g. KOH activation, Sargassum",
            label_visibility="visible",
        )
    with col2:
        tier_filter = st.selectbox("Tier", ["All", "core", "supporting", "tangential"])
    with col3:
        year_from = st.number_input("Year from", min_value=2000, max_value=2026, value=2009, step=1)
    with col4:
        oa_filter = st.selectbox("Open Access", ["All", "Yes", "No"])

    tier_param    = None if tier_filter == "All" else tier_filter
    oa_param      = None if oa_filter   == "All" else (oa_filter == "Yes")
    keyword_param = keyword.strip() if keyword.strip() else None

    data   = fetch_papers(tier=tier_param, year_from=int(year_from),
                          year_to=None, open_access=oa_param, keyword=keyword_param)
    papers = data.get("results", [])
    total  = data.get("total", 0)

    st.markdown(
        f"<p style='font-size:12px;color:#747474;letter-spacing:0.4px;"
        f"text-transform:uppercase;margin-bottom:12px;'>"
        f"{total} PAPER(S) FOUND</p>",
        unsafe_allow_html=True,
    )

    if not papers:
        st.info("No papers match the current filters.")
    else:
        for paper in papers:
            tier_dot = TIER_COLOURS.get(paper.get("tier", ""), "⚪")
            oa_badge = "🔓" if paper.get("open_access") else "🔒"
            year     = paper.get("year") or "n.d."
            title    = paper.get("title", "Untitled")
            paper_id = paper.get("id")

            with st.expander(f"{tier_dot} {oa_badge} [{year}]  {title[:85]}"):
                st.markdown(
                    f"<span style='color:#747474;font-size:12px;'>AUTHORS</span><br>"
                    f"<span style='font-size:13px;'>{paper.get('authors', '—')}</span>",
                    unsafe_allow_html=True,
                )
                doi = paper.get("doi", "")
                doi_inline = (
                    f" &nbsp;<a href='https://doi.org/{doi}' target='_blank' "
                    f"style='color:#ff4d00;font-size:12px;text-decoration:none;"
                    f"border-bottom:1px solid #ff4d00;'>→ DOI</a>"
                    if doi else ""
                )
                st.markdown(
                    f"<span style='color:#747474;font-size:12px;'>JOURNAL</span><br>"
                    f"<span style='font-size:13px;'>{paper.get('journal', '—')}</span>"
                    f"{doi_inline}",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<span style='color:#747474;font-size:11px;'>TIER: "
                    f"<span style='color:#efefef;'>{paper.get('tier','—').upper()}</span></span>",
                    unsafe_allow_html=True,
                )
                if st.button("VIEW DETAIL →", key=f"detail_{paper_id}"):
                    st.session_state["detail_paper_id"] = paper_id
                    st.session_state["nav_override"] = "🔬  PAPER DETAIL"
                    st.rerun()


# ---------------------------------------------------------------------------
# View 2 — Paper Detail
# ---------------------------------------------------------------------------
elif view == "🔬  PAPER DETAIL":
    st.title("Paper Detail")

    paper_id_input = st.number_input(
        "PAPER ID",
        min_value=1,
        step=1,
        value=st.session_state.get("detail_paper_id", 1),
    )

    paper = fetch_paper(int(paper_id_input))

    if paper is None:
        st.warning(f"No paper found with id={paper_id_input}.")
    else:
        tier_dot = TIER_COLOURS.get(paper.get("tier", ""), "⚪")
        oa_label = "OPEN ACCESS" if paper.get("open_access") else "PAYWALLED"
        doi      = paper.get("doi", "")
        doi_html = (
            f" · <a href='https://doi.org/{doi}' target='_blank' "
            f"style='color:#ff4d00;text-decoration:none;"
            f"border-bottom:1px solid #ff4d00;'>DOI →</a>"
            if doi else ""
        )

        st.markdown(
            f"<h2 style='font-size:17px!important;font-weight:700;"
            f"letter-spacing:0.1px;color:#efefef!important;"
            f"text-transform:none!important;margin-bottom:4px;'>"
            f"{paper.get('title', 'Untitled')}</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='font-size:12px;color:#747474;margin-top:0;'>"
            f"{tier_dot} <span style='color:#ff4d00;'>"
            f"{paper.get('tier','').upper()}</span>"
            f" · {oa_label} · {paper.get('year') or 'n.d.'}"
            f"{doi_html}</p>",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"<p style='font-size:13px;margin-bottom:4px;'>"
            f"<span style='color:#747474;'>AUTHORS</span><br>"
            f"{paper.get('authors', '—')}</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='font-size:13px;'>"
            f"<span style='color:#747474;'>JOURNAL</span><br>"
            f"{paper.get('journal', '—')}</p>",
            unsafe_allow_html=True,
        )

        st.markdown("<hr style='border-color:#3a3a3a;margin:16px 0;'/>", unsafe_allow_html=True)

        abstract = paper.get("abstract", "")
        if abstract:
            with st.expander("ABSTRACT", expanded=True):
                st.markdown(
                    f"<p style='font-size:13px;line-height:1.6;color:#efefef;'>"
                    f"{abstract}</p>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("No abstract available for this paper.")

        st.markdown("<hr style='border-color:#3a3a3a;margin:16px 0;'/>", unsafe_allow_html=True)

        properties = paper.get("properties", [])
        st.markdown(
            f"<p style='font-size:12px;color:#747474;letter-spacing:0.4px;"
            f"text-transform:uppercase;margin-bottom:8px;'>"
            f"EXTRACTED PROPERTIES ({len(properties)})</p>",
            unsafe_allow_html=True,
        )

        if not properties:
            st.info(
                "No properties extracted. This is likely a review paper "
                "or the abstract contained no numeric values."
            )
        else:
            prop_df = pd.DataFrame([
                {
                    "Type":       PROPERTY_LABELS.get(p["property_type"], p["property_type"]),
                    "Value":      p["value"],
                    "Unit":       p.get("unit") or "—",
                    "Conditions": clean_conditions(p.get("conditions", "")),
                    "Confidence": p.get("confidence", 0),
                    "Method":     p.get("extraction_method", ""),
                }
                for p in properties
            ])
            st.dataframe(
                prop_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Confidence": st.column_config.ProgressColumn(
                        "Confidence", min_value=0.0, max_value=1.0, format="%.2f",
                    )
                },
            )


# ---------------------------------------------------------------------------
# View 3 — Properties Comparison
# ---------------------------------------------------------------------------
elif view == "📊  PROPERTIES":
    st.title("Properties Comparison")
    st.caption(
        "Compare extracted material properties across papers. "
        "Numeric properties render as a ranked chart."
    )

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        prop_type = st.selectbox(
            "Property type",
            options=list(PROPERTY_LABELS.keys()),
            format_func=lambda k: PROPERTY_LABELS[k],
        )
    with col2:
        tier_filter = st.selectbox(
            "Tier", ["All", "core", "supporting", "tangential"], key="prop_tier"
        )
    with col3:
        min_conf = st.slider("Min confidence", 0.0, 1.0, 0.7, 0.05)

    tier_param = None if tier_filter == "All" else tier_filter
    data       = fetch_properties(property_type=prop_type, tier=tier_param,
                                  min_confidence=min_conf)
    results    = data.get("results", [])
    total      = data.get("total", 0)

    st.markdown(
        f"<p style='font-size:12px;color:#747474;letter-spacing:0.4px;"
        f"text-transform:uppercase;margin-bottom:12px;'>"
        f"{total} EXTRACTED VALUE(S)</p>",
        unsafe_allow_html=True,
    )

    if not results:
        st.info("No properties match the current filters.")
    else:
        rows = []
        for r in results:
            rows.append({
                "Paper":      r["paper_title"][:70] + ("…" if len(r["paper_title"]) > 70 else ""),
                "Year":       r.get("paper_year") or "n.d.",
                "Tier":       TIER_COLOURS.get(r["paper_tier"], "⚪") + " " + r["paper_tier"],
                "Value":      r["value"],
                "Unit":       r.get("unit") or "—",
                "Conditions": clean_conditions(r.get("conditions", "")),
                "DOI":        r.get("paper_doi", ""),
                "_numeric":   None,
            })

        numeric_values = []
        for row in rows:
            try:
                row["_numeric"] = float(row["Value"])
                numeric_values.append(row["_numeric"])
            except (ValueError, TypeError):
                pass

        df = pd.DataFrame(rows)

        is_numeric_type = prop_type != "activating_agent"
        has_numeric     = len(numeric_values) > 0

        if is_numeric_type and has_numeric:
            chart_df = (
                df[df["_numeric"].notna()]
                .copy()
                .sort_values("_numeric", ascending=True)
                .reset_index(drop=True)
            )
            chart_df["Label"] = (
                chart_df["Paper"].str[:50]
                + " ("
                + chart_df["Year"].astype(str)
                + ")"
            )

            st.markdown(
                f"<p style='font-size:12px;color:#747474;letter-spacing:0.4px;"
                f"text-transform:uppercase;margin-bottom:4px;'>"
                f"{PROPERTY_LABELS[prop_type]} — RANKED</p>",
                unsafe_allow_html=True,
            )

            # Fixed height — fits in viewport without scrolling
            chart_height = min(320, max(200, len(chart_df) * 38))
            st.bar_chart(
                chart_df.set_index("Label")["_numeric"],
                use_container_width=True,
                height=chart_height,
            )
            st.caption(
                f"Range: {min(numeric_values):.1f} – {max(numeric_values):.1f} "
                f"{results[0].get('unit') or ''}"
            )

        st.markdown(
            "<hr style='border-color:#3a3a3a;margin:16px 0;'/>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<p style='font-size:12px;color:#747474;letter-spacing:0.4px;"
            "text-transform:uppercase;margin-bottom:8px;'>ALL EXTRACTED VALUES</p>",
            unsafe_allow_html=True,
        )

        display_df = df.drop(columns=["_numeric"]).rename(columns={"DOI": "DOI (link)"})
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "DOI (link)": st.column_config.LinkColumn("DOI", display_text="→ link")
            },
        )

        # Research gap callout
        if tier_param == "core" and prop_type == "specific_capacitance":
            st.markdown(
                "<hr style='border-color:#3a3a3a;margin:16px 0;'/>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div style='border-left:3px solid #ff4d00;padding:10px 16px;"
                "background:#1a1a1a;border-radius:2.8px;font-size:13px;"
                "line-height:1.6;'>"
                "<span style='color:#ff4d00;font-weight:700;letter-spacing:0.4px;'>"
                "RESEARCH GAP</span><br>"
                "All capacitance values above are from non-Philippine seaweed species "
                "(Sargassum, Ulva, Gracilaria). "
                "Zero published results exist for <em>Eucheuma cottonii</em> or "
                "<em>Kappaphycus alvarezii</em> as supercapacitor electrode materials — "
                "the primary Philippine commercial species."
                "</div>",
                unsafe_allow_html=True,
            )