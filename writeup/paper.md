# Bagong Enerhiya: An AI-Assisted Literature Intelligence Tool for Philippine Macroalgae Supercapacitor Materials Research

**Author:** Arenga, Jan Mico M.
**Affiliation:** Incoming BS AI Engineering Student, Mapúa University, Manila, Philippines
**Date:** June 2026
**Repository:** https://github.com/SpIob/Bagong-Enerhiya

---

## Abstract

The global push for renewable energy storage has intensified interest in biomass-derived carbon electrode materials for supercapacitors. Despite the Philippines being the world's foremost producer of commercially farmed macroalgae — specifically *Eucheuma cottonii* and *Kappaphycus alvarezii* — no published research exists on these species as supercapacitor electrode precursors. This paper presents Bagong Enerhiya, a zero-budget, open-source literature intelligence platform designed to surface this gap and support its investigation. The system ingests scientific literature from Semantic Scholar and CrossRef, extracts material properties (specific capacitance, BET surface area, pyrolysis temperature, activating agent) from paper abstracts using a MatSciBERT-backed NLP pipeline with regex post-processing, and exposes the resulting structured dataset through a FastAPI backend and an interactive Streamlit interface. Applied to a 62-paper corpus spanning 2009–2026, the tool identifies a specific capacitance range of 45.9–354 F/g across seaweed-derived carbon electrodes, with zero Philippine-species-specific data points — confirming the research gap programmatically. Bagong Enerhiya demonstrates that literature intelligence systems are viable standalone research contributions in materials science, and provides a reusable open-source framework for future computational chemistry research on Philippine natural resources.

---

## 1. Introduction

### 1.1 Supercapacitors and Biomass-Derived Carbon Electrodes

Supercapacitors (electrochemical double-layer capacitors, EDLCs) occupy a critical position in the energy storage landscape: they deliver high power density and exceptional cycle life compared to batteries, making them suitable for applications in electric vehicles, grid stabilization, and portable electronics [1]. The performance of an EDLC is largely determined by its electrode material. Activated carbon dominates commercial production, but its manufacture from fossil-derived precursors raises sustainability concerns and cost barriers for developing economies [2].

Biomass-derived carbon has emerged as a compelling alternative. Agricultural and marine waste streams can be converted into porous carbon electrodes through pyrolysis and chemical activation, producing materials with competitive surface areas and electrochemical properties [3]. Among marine biomass, macroalgae (seaweed) has attracted particular attention: its naturally high heteroatom content (nitrogen, sulfur, oxygen) from proteins and polysaccharides enables self-doping during carbonization, enhancing pseudocapacitive contributions without external chemical precursors [4].

### 1.2 Philippine Macroalgae as an Underexplored Resource

The Philippines is the world's largest producer of *Eucheuma cottonii* and *Kappaphycus alvarezii*, two red macroalgae cultivated primarily for carrageenan extraction [5]. Annual production exceeds 1.5 million metric tons of wet biomass, and the post-extraction solid residue — rich in cellulose and residual polysaccharides — is typically discarded as waste [6]. This represents a significant untapped precursor stream for carbon electrode synthesis.

Despite the material abundance, a systematic review of the literature reveals a striking gap: as of mid-2026, there are fewer than 50 publications globally on seaweed biochar for electrochemical energy storage applications, and zero papers specifically investigating *Eucheuma* or *Kappaphycus* as supercapacitor electrode precursors. Related seaweed species (Sargassum, Ulva, Gracilaria) have been studied to varying degrees, with reported capacitances ranging from 45.9 F/g to 354 F/g [7–12], but Philippine commercial species remain entirely unstudied in this context.

### 1.3 The Fragmentation Problem and Rationale for a Literature Intelligence Tool

Research progress in this domain is hampered by fragmentation: relevant findings are distributed across materials science, energy engineering, marine biology, and chemical engineering journals without a unified data resource. A researcher seeking to design a synthesis protocol for *K. alvarezii*-derived carbon electrodes must manually aggregate data on pyrolysis temperatures, activating agents, and electrochemical outcomes from dozens of papers reporting different experimental conditions with no standardized reporting format.

This problem is well-suited to AI-assisted literature intelligence. Natural language processing tools trained on scientific corpora can extract structured property data from paper abstracts at scale, converting unstructured text into queryable databases. The contribution of such a tool is not the experimental data itself, but the infrastructure for discovering, comparing, and identifying gaps in existing knowledge — a research contribution in its own right.

### 1.4 Research Objectives

This paper presents Bagong Enerhiya, an open-source platform that:

1. Builds a structured, queryable corpus of seaweed-derived carbon electrode literature.
2. Extracts material properties automatically from paper abstracts using a domain-adapted NLP pipeline.
3. Exposes the corpus and extracted data through a web interface accessible to Filipino researchers without institutional database subscriptions.
4. Quantifies the research gap for Philippine macroalgae species programmatically.

---

## 2. Methodology

### 2.1 System Architecture

Bagong Enerhiya is a three-layer system: a data layer (SQLite database), a logic layer (FastAPI backend), and a presentation layer (Streamlit interface). Figure 1 illustrates the architecture.

```
Literature APIs          Ingestion Pipeline         Database
(Semantic Scholar,  →   fetch_papers.py         →  bagong_enerhiya.db
 CrossRef)               search_papers.py           (papers, properties)
                         extract.py                      ↓
                                                    FastAPI (api/main.py)
                                                    GET /papers
                                                    GET /papers/{id}
                                                    GET /properties
                                                         ↓
                                                    Streamlit UI
                                                    (app/streamlit_app.py)
                                                    Paper Browser
                                                    Paper Detail
                                                    Properties Comparison
```

The entire stack uses zero-cost open-source tools and free API tiers, making it reproducible without institutional resources. The database schema defines two core tables: `papers` (bibliographic metadata) and `properties` (extracted material properties linked to papers), with a `tier` classification system (core, supporting, tangential) encoding relevance to the anchor research question.

### 2.2 Data Collection and Corpus Construction

#### 2.2.1 Primary Corpus (14 papers)

An initial corpus of 14 papers was assembled manually from the literature, covering the period 2009–2024. Inclusion criteria required papers to involve seaweed or macroalgae as a carbon precursor, target electrochemical energy storage as the application, and be identifiable by DOI. Papers were assigned tiers:

- **Core:** seaweed/macroalgae carbon directly tested as supercapacitor or battery electrode material.
- **Supporting:** seaweed characterization, pyrolysis parameters, or biochar synthesis without electrochemical testing.
- **Tangential:** *Kappaphycus* or *Eucheuma* studies in non-energy contexts (pharmaceutical, agricultural, corrosion).

Bibliographic metadata was retrieved automatically from CrossRef using DOIs, with HTML entity decoding applied to normalize special characters in titles and journal names.

#### 2.2.2 Corpus Expansion via Semantic Scholar

The corpus was expanded using the Semantic Scholar Graph API with five keyword queries targeting seaweed carbon electrode literature. Results were filtered by pre-flight DOI deduplication and post-insertion tier correction to remove off-topic papers that slipped through broad queries. The final corpus comprised 62 papers spanning 2009–2026, with 25 classified as core, 30 as supporting, and 7 as tangential. Of the 62 papers, 18 (29%) are open-access.

#### 2.2.3 Search Strategy and Limitations

The queries used were: (1) *seaweed macroalgae biochar supercapacitor*, (2) *Sargassum Gracilaria Ulva carbon electrode supercapacitor*, (3) *seaweed derived nitrogen doped carbon supercapacitor*, (4) *macroalgae pyrolysis activated carbon electrochemical*, (5) *biomass KOH activated carbon supercapacitor seaweed*. A query explicitly targeting *Kappaphycus alvarezii* and *Eucheuma* carbon electrodes returned no relevant results, which is itself a significant finding documented in Section 3.3.

A key limitation is paywall coverage: 71% of papers are not open-access, meaning abstract-level extraction was possible but full-text data was unavailable for the majority. Future work should integrate open-access preprint repositories (arXiv, ChemRxiv) to improve coverage.

### 2.3 NLP Property Extraction Pipeline

#### 2.3.1 Model Selection

Two domain-adapted BERT models were evaluated as zero-shot token classification backbones: `allenai/scibert_scivocab_uncased` (SciBERT) [13] and `m3rg-iitd/matscibert` (MatSciBERT) [14]. Both were loaded using HuggingFace's `token-classification` pipeline with `aggregation_strategy="simple"` to merge subword tokens.

Evaluation was conducted on three anchor paper abstracts (Yang et al. 2022 [7], Jiang et al. 2021 [8], Liu & Yang 2023 [15]) with entity vocabulary matching against four target property types. MatSciBERT was selected based on three qualitative advantages: superior span coherence (grouping numeric values with their units into single spans), higher activating agent recall (correctly identifying NaCl that SciBERT missed), and higher-confidence consolidated spans for pyrolysis temperature.

#### 2.3.2 Extraction Architecture

The final extraction pipeline (`pipeline/extract.py`) uses a hybrid approach: regex-primary extraction for specific capacitance, BET surface area, and pyrolysis temperature, with keyword-lookup extraction for activating agents. This design reflects the empirical finding that MatSciBERT is most valuable for span detection in ambiguous contexts, while regex is more reliable for extracting precise numeric values and units from abstracts with consistent reporting patterns.

Four entity types were targeted:

| Property Type | Extraction Method | Regex Pattern | Unit |
|---|---|---|---|
| `specific_capacitance` | Regex | `(\d[\d,.]*)\s*[Ff]\s*[g/]?[-−]?\s*1?` | F/g |
| `BET_surface_area` | Regex | `(\d[\d,.]*)\s*m[²2]\s*[g/]?[-−]?\s*1?` | m²/g |
| `pyrolysis_temp` | Regex + context window | `(\d{3,4})\s*[°º]?\s*[Cc]` near pyrolysis keywords | °C |
| `activating_agent` | Keyword lookup | Known agents: KOH, NaOH, ZnCl₂, H₃PO₄, NaCl, etc. | — |

The database schema stores each extracted property with a `confidence` score (0.75–0.90 depending on extraction method), an `extraction_method` flag (manual, nlp, or llm), and a `conditions` field capturing test context (e.g., "at 0.5 A/g in 6M KOH") for normalization purposes.

#### 2.3.3 Post-Extraction Quality Control

Manual review of extracted properties identified two categories of false positives: (1) activating agents extracted from supporting/tangential tier papers where KOH or NaOH are extraction solvents rather than electrode activation reagents; (2) a single-digit false positive value ("1") extracted from a chart label. These were corrected via targeted SQL `DELETE` and `UPDATE` queries, and the `tier` filter in the API was confirmed to suppress false positives in the UI's core-tier view.

Duplicate extraction rows arising from running the pipeline twice were removed using a `DELETE WHERE id NOT IN (SELECT MIN(id) GROUP BY paper_id, property_type, value, extraction_method)` query.

### 2.4 Backend API

The FastAPI backend exposes three endpoints:

- `GET /papers` — returns papers with optional filters for `tier`, `year_from`, `year_to`, `open_access`, and full-text `keyword` search across title and abstract. Supports pagination via `limit` and `offset`.
- `GET /papers/{id}` — returns full metadata for a single paper including all extracted properties.
- `GET /properties` — returns cross-paper property records, filterable by `property_type`, `tier`, `min_confidence`, and `extraction_method`. Designed for the comparison table view.

All endpoints return paginated JSON with total counts. CORS is enabled for all origins to support the Streamlit frontend and external API consumers. Auto-generated API documentation is available at `/docs` (Swagger UI) and `/redoc`.

### 2.5 User Interface

The Streamlit interface (`app/streamlit_app.py`) provides three views:

**Paper Browser** — a searchable, filterable list of all corpus papers. Filters include tier (core / supporting / tangential), year range, and open-access status. Each paper is displayed as an expandable card showing authors, journal, DOI link, and tier badge, with a navigation button to the Paper Detail view.

**Paper Detail** — full bibliographic metadata, abstract, and a structured table of extracted properties with confidence scores rendered as progress bars.

**Properties Comparison** — a ranked bar chart and full comparison table for any selected property type across the corpus. Filtering to `tier=core` and `property_type=specific_capacitance` displays the research gap callout, which states explicitly that all tabulated values are from non-Philippine seaweed species.

The interface uses a monospace dark theme with an orange accent color (`#ff4d00`) chosen to reference the visual language of technical computing environments, consistent with the research tool's intended academic user base.

---

## 3. Results and Discussion

### 3.1 Corpus Overview

The final corpus of 62 papers spans 17 years (2009–2026), with a marked increase in publication volume from 2020 onwards reflecting the broader surge in biomass-derived electrode research. The 25 core papers cover seven macroalgae genera: Sargassum (7 papers), Ulva (4), Gracilaria (3), Caulerpa (2), Chlorella and Spirulina microalgae (2), seaweed unspecified (7). The Philippine priority species (*Eucheuma*, *Kappaphycus*) appear in the corpus only in supporting and tangential contexts — pharmaceutical, agricultural, and carrageenan extraction studies — with zero core papers.

### 3.2 Extracted Property Performance

The extraction pipeline produced 10 property rows from the initial 14-paper corpus and approximately 65 rows following corpus expansion to 62 papers. After deduplication and false positive removal, 8 valid specific capacitance values were confirmed for core-tier seaweed papers:

| Paper | Species | Capacitance (F/g) | Conditions |
|---|---|---|---|
| Roche et al. 2023 [10] | Sargassum | 96 | — |
| Yang et al. 2022 [7] | Seaweed (unspecified) | 110.8 | 1 A/g |
| Gang et al. 2021 [11] | Ulva lactuca | 167 | 1.0 A/g, two-electrode |
| Jiang et al. 2021 [8] | Seaweed fibre | 226.3 | 900°C carbonisation |
| Li et al. 2022 [9] | Sargassum | 237.3 | 0.5 A/g, 6M KOH |
| Jia et al. 2020 [12] | Sargassum | 336 | 1 A/g |
| Divya et al. 2019 [12] | Sargassum Wightii | 354 | — |
| K.S. et al. 2025 [—] | Gracilaria spinulosa | 45.9 | 0.5 A/g |

The range of 45.9–354 F/g reflects the broad influence of species, activation method, and testing conditions. The wide variance underscores the normalization challenge noted in the open questions: direct comparison across studies requires harmonizing current density, electrolyte, and electrode configuration, which abstract-level extraction cannot fully resolve. The `conditions` field captures partial context, but full normalization requires full-text access.

BET surface area extraction succeeded for two papers (603.7 m²/g for Yang et al. 2022; 1,300 m²/g for Raymundo-Piñero et al. 2009), and activating agent extraction identified KOH, NaCl, and NaOH across core papers. Pyrolysis temperatures of 900°C and 800°C were extracted from two core papers.

### 3.3 The Philippine Species Gap — Quantified

The most significant finding is confirmatory rather than generative: when the corpus is filtered to `tier=core`, no extracted properties exist for *Eucheuma cottonii* or *Kappaphycus alvarezii*. This is not an extraction failure — it reflects the actual state of the literature. The Semantic Scholar query explicitly targeting these species by name returned zero relevant results, and manual review confirmed that all *Kappaphycus* and *Eucheuma* papers in the corpus are classified as supporting or tangential.

This gap is significant for two reasons. First, these species possess structural properties that suggest electrode potential: *K. alvarezii* has a high sulfur content from its floridean starch and sulfated polysaccharides [16], which could contribute to heteroatom self-doping during pyrolysis — a property associated with enhanced pseudocapacitance in nitrogen- and sulfur-doped biochars [4]. Second, the Philippines' production dominance means that any synthesis protocol developed for these species could be implemented at industrial scale without supply chain constraints.

The Bagong Enerhiya tool makes this gap immediately visible to any researcher accessing the Properties Comparison view, and provides the supporting literature context (related seaweed electrode studies) needed to design the first experimental investigation.

### 3.4 Tool Contributions and Limitations

Bagong Enerhiya demonstrates several contributions beyond its specific research application. The corpus expansion workflow (automated DOI-based metadata ingestion from CrossRef, keyword-based discovery from Semantic Scholar) is generalizable to any biomass electrode subfield. The tiered relevance classification system provides a transparent mechanism for filtering signal from noise in broadly queried corpora. The FastAPI backend exposes the structured dataset as a public API, enabling programmatic access for downstream analysis by other researchers.

Key limitations include: (1) abstract-level extraction misses numeric data reported only in tables, figures, or supplementary materials; (2) the 71% paywall rate in the corpus limits extraction coverage; (3) the regex-based approach assumes consistent unit reporting conventions that not all papers follow (e.g., mF/cm² vs. F/g); (4) the corpus of 62 papers, while focused, is small relative to the broader biomass carbon literature, and expanding beyond seaweed species would require retraining the entity extraction on a larger annotated set.

---

## 4. Conclusion

This paper has presented Bagong Enerhiya, an AI-assisted literature intelligence platform that systematically maps the state of seaweed-derived carbon electrode research with specific attention to Philippine macroalgae species. The core finding is a confirmed zero: despite the Philippines' global dominance in macroalgae production, no published research exists characterizing *Eucheuma cottonii* or *Kappaphycus alvarezii* as supercapacitor electrode precursors. The tool makes this gap visible and actionable by providing the full context of related seaweed electrode literature — eight confirmed capacitance data points from 2019–2025 across Sargassum, Ulva, and Gracilaria species — alongside the structural context needed to motivate an experimental program.

The project demonstrates that a solo student researcher with a computer science background, zero budget, and four weeks can build a functional research intelligence platform that makes a genuine contribution to the materials science literature. The full codebase, database, and documentation are available at https://github.com/SpIob/Bagong-Enerhiya under the MIT License.

### Future Work

Immediate next steps include: (1) conducting the first experimental synthesis and electrochemical characterization of *K. alvarezii*-derived activated carbon electrodes using the protocols identified in the literature review; (2) expanding the extraction pipeline to heteroatom content and cycling stability to enable more complete cross-paper comparison; (3) fine-tuning MatSciBERT on a hand-annotated set of 50–100 seaweed electrode abstracts to improve precision on BET surface area extraction; (4) integrating a synthesis condition prediction module that recommends pyrolysis temperature and activating agent ratios based on target capacitance. Longer-term, the platform could be extended to other Philippine natural resources — nickel laterite ores, coconut shell, bamboo biochar — with species-specific extraction schemas for each material class.

---

## References

[1] B.E. Conway, *Electrochemical Supercapacitors: Scientific Fundamentals and Technological Applications*, Springer, 1999.

[2] M. Inagaki, H. Konno, O. Tanaike, "Carbon materials for electrochemical capacitors," *J. Power Sources*, vol. 195, pp. 7880–7903, 2010.

[3] Y. Wang et al., "Recent advances in biomass derived activated carbon electrodes for high-performance energy storage systems," *Carbon*, vol. 168, pp. 438–455, 2020. https://doi.org/10.1016/j.carbon.2020.07.056

[4] X. Liu, H. Yang, "A state-of-the-art review of N self-doped biochar development in supercapacitor applications," *Frontiers in Energy Research*, 2023. https://doi.org/10.3389/fenrg.2023.1135093

[5] FAO, *The State of World Fisheries and Aquaculture 2022*, Food and Agriculture Organization of the United Nations, Rome, 2022.

[6] F. Masarin et al., "Chemical analysis and biorefinery of red algae *Kappaphycus alvarezii* for efficient production of glucose from residue of carrageenan extraction process," *Biotechnology for Biofuels*, vol. 9, 2016. https://doi.org/10.1186/s13068-016-0535-9

[7] W.-D. Yang et al., "Preparatory Conditions Optimization and Characterization of Hierarchical Porous Carbon from Seaweed as Carbon-Precursor Using a Box–Behnken Design for Application of Supercapacitor," *Materials*, vol. 15, p. 5748, 2022. https://doi.org/10.3390/ma15165748

[8] L. Jiang et al., "Seaweed biomass waste-derived carbon as an electrode material for supercapacitor," *Energy & Environment*, 2021. https://doi.org/10.1177/0958305X19882398

[9] S. Li et al., "Investigation on pore structure regulation of activated carbon derived from sargassum and its application in supercapacitor," *Scientific Reports*, 2022. https://doi.org/10.1038/s41598-022-14214-w

[10] S. Roche et al., "Carbon Materials Prepared from Invading Pelagic Sargassum for Supercapacitors' Electrodes," *Molecules*, vol. 28, p. 5882, 2023. https://doi.org/10.3390/molecules28155882

[11] B.-G. Gang et al., "A ulva lactuca-derived porous carbon for high-performance electrode materials in supercapacitor," *Journal of Energy Storage*, 2021. https://doi.org/10.1016/j.est.2020.102132

[12] X. Jia et al., "Synthesis of porous carbon materials with mesoporous channels from Sargassum as electrode materials for supercapacitors," *Journal of Electroanalytical Chemistry*, 2020. https://doi.org/10.1016/j.jelechem.2020.114353

[13] I. Beltagy, K. Lo, A. Cohan, "SciBERT: A Pretrained Language Model for Scientific Text," *EMNLP*, 2019.

[14] T. Gupta et al., "MatSciBERT: A materials domain language model for text mining and information extraction," *npj Computational Materials*, 2022.

[15] P. Divya, A. Prithiba, R. Rajalakshmi, "Biomass derived functional carbon from Sargassum Wightii seaweed for supercapacitors," *IOP Conf. Series*, 2019. https://doi.org/10.1088/1757-899X/561/1/012078

[16] L. Mendes et al., "Advanced Extraction Techniques and Physicochemical Properties of Carrageenan from a Novel *Kappaphycus alvarezii* Cultivar," *Marine Drugs*, 2024. https://doi.org/10.3390/md22110491