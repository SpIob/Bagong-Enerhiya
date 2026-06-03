-- =============================================================================
-- Bagong Enerhiya — Database Schema
-- =============================================================================
-- Two core tables:
--   papers     : bibliographic metadata for each source paper
--   properties : extracted material properties linked to a paper
--
-- Tiers:
--   core       : seaweed/macroalgae carbon tested for electrochemical storage
--   supporting : seaweed characterization, pyrolysis, or biochar adjacent work
--   tangential : K. alvarezii studies outside energy storage scope
--
-- Property types (properties.property_type):
--   specific_capacitance   F/g or mF/cm²
--   BET_surface_area       m²/g
--   pyrolysis_temp         °C
--   activating_agent       e.g. KOH, ZnCl₂, CO₂, NaOH, none
--   heteroatom_content     % N, O, or S
--   cycling_stability      % retention over N cycles
--   energy_density         Wh/kg
--   power_density          W/kg
-- =============================================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- papers
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS papers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Bibliographic metadata
    title           TEXT    NOT NULL,
    authors         TEXT,                   -- comma-separated author names
    year            INTEGER,
    journal         TEXT,
    doi             TEXT    UNIQUE,         -- canonical identifier; NULL for patents
    abstract        TEXT,

    -- Corpus management
    tier            TEXT    NOT NULL DEFAULT 'core'
                    CHECK (tier IN ('core', 'supporting', 'tangential')),
    open_access     INTEGER NOT NULL DEFAULT 0
                    CHECK (open_access IN (0, 1)),  -- 1 = full text freely available

    -- Audit
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Speeds up tier-based filtering in the Streamlit UI
CREATE INDEX IF NOT EXISTS idx_papers_tier ON papers (tier);

-- Speeds up year-range filtering
CREATE INDEX IF NOT EXISTS idx_papers_year ON papers (year);

-- -----------------------------------------------------------------------------
-- properties
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS properties (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id        INTEGER NOT NULL REFERENCES papers (id) ON DELETE CASCADE,

    -- Extracted entity
    property_type   TEXT    NOT NULL
                    CHECK (property_type IN (
                        'specific_capacitance',
                        'BET_surface_area',
                        'pyrolysis_temp',
                        'activating_agent',
                        'heteroatom_content',
                        'cycling_stability',
                        'energy_density',
                        'power_density'
                    )),
    value           TEXT    NOT NULL,       -- raw extracted value, e.g. "278.5"
    unit            TEXT,                   -- e.g. "F/g", "m²/g", "°C", NULL for agents
    conditions      TEXT,                   -- test context, e.g. "0.5 A/g in 6M KOH"

    -- Extraction provenance
    confidence      REAL    NOT NULL DEFAULT 1.0
                    CHECK (confidence BETWEEN 0.0 AND 1.0),
    extraction_method   TEXT NOT NULL DEFAULT 'manual'
                        CHECK (extraction_method IN ('manual', 'nlp', 'llm')),

    -- Audit
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Speeds up per-paper property lookups and per-type aggregation queries
CREATE INDEX IF NOT EXISTS idx_properties_paper_id    ON properties (paper_id);
CREATE INDEX IF NOT EXISTS idx_properties_type        ON properties (property_type);