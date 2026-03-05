# scripts/

This directory contains versioned implementations of the **Lattes XML to PDF Converter**. Each version folder ships its own Python script, metadata descriptor, and test suite. A shared notebook at the directory root provides cross-version inspection and test orchestration.

---

## Directory Structure

```
scripts/
├── test_suite.ipynb          # Cross-version inspector and pytest orchestrator
├── README.md                 # This file
│
├── v1/                       # Version 1 — initial terminal refactor
│   ├── lattes_para_pdf.py    # Standalone CLI script (no Jupyter dependency)
│   ├── metadata.json         # Version descriptor
│   └── tests/
│       └── test_lattes_para_pdf.py  # pytest test suite (functional, no mocks)
│
├── v2/                       # Reserved for future versions
├── v3/                       # Reserved for future versions
└── v4/                       # Reserved for future versions
```

---

## Versioning Policy

| Rule | Detail |
|------|--------|
| **One folder per version** | `v1/`, `v2/`, … Each version is self-contained. |
| **`metadata.json` required** | Every version folder must carry a `metadata.json` (schema below). |
| **`tests/` sub-folder** | Functional tests live under `<version>/tests/`. |
| **No cross-version imports** | Each version script must be independently runnable. |
| **Backward compatibility** | A new version folder is created for breaking changes; old versions are not deleted. |

---

## metadata.json Schema

Every version folder must contain a `metadata.json` file with the following fields:

```jsonc
{
  "script":            "lattes_para_pdf.py",   // entry-point file name
  "version":           "1.0.0",                // semantic version
  "created_at":        "YYYY-MM-DD",
  "last_modified_at":  "YYYY-MM-DD",
  "author":            "repository name or author",
  "description":       "Human-readable description of this version.",
  "language":          "python",
  "entry_point":       "lattes_para_pdf.py",
  "runtime":           "python>=3.9",
  "dependencies": {
    "runtime": ["reportlab>=4.0.0"],
    "stdlib":  ["argparse", "pathlib", ...]
  },
  "usage": {
    "basic": "python lattes_para_pdf.py <ZIP_FILE>"
  },
  "exit_codes": {
    "0": "Success",
    "1": "User / argument error",
    "2": "File or environment error",
    "3": "PDF generation error"
  },
  "sections_extracted": [...],
  "source_notebook": "../../lattes_para_pdf.ipynb",
  "changelog": [
    { "version": "1.0.0", "date": "YYYY-MM-DD", "notes": "..." }
  ],
  "known_limitations": [...]
}
```

The `test_suite.ipynb` notebook reads these fields to produce the metadata report.

---

## v1 — Detailed Documentation

### Purpose

`v1/lattes_para_pdf.py` is a **terminal-based** refactor of the root-level `lattes_para_pdf.ipynb` notebook. It preserves 100 % of the extraction and PDF-rendering logic while eliminating all Jupyter-specific dependencies (`tqdm.notebook`, `ipywidgets`, `IPython.display`).

> **Note:** The interactive CV editor (Block 5 of the notebook) is intentionally excluded. Terminal-mode editing is out of scope for v1.

### Architecture

```
lattes_para_pdf.py
│
├── Sections 0–1  : CLI argument parsing (_parse_args)
├── Section 2     : ZIP/XML resolution (_resolve_zip, extract_xml)
├── Sections 3–4  : XML utility helpers (_attr, _fmt_date, _period, _safe)
├── Section 5     : Data extraction layer
│   ├── extract_personal
│   ├── extract_education
│   ├── extract_experience
│   ├── extract_internships
│   ├── extract_research
│   ├── extract_publications
│   ├── extract_areas
│   ├── extract_languages
│   ├── extract_awards
│   └── extract_events
├── Section 6     : Extraction pipeline (run_pipeline)
├── Section 7     : Font registration (_register_fonts)
├── Section 8     : ReportLab style system (_build_styles)
├── Sections 9–10 : Layout primitives and section builders
│   ├── _make_primitives  (_p, _pm, _b, _hr, _sp, _section_header)
│   └── _make_builders    (build_header, build_education, …)
├── Section 11    : Document assembly (generate_pdf)
└── Section 12    : Entry point (main)
```

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Pure functions per section** | Each extraction function receives an `ET.Element` root and returns `dict` or `list[dict]`. No global state in extraction layer. |
| **Factory pattern for primitives/builders** | `_make_primitives` and `_make_builders` return callables bound to the active style dict, avoiding global `ST` singletons. Enables clean testability. |
| **Encoding strategy documented inline** | ReportLab XML parsing has subtle UTF-8/escape interaction. Strategy (`_safe`, `_p`, `_pm`) is documented at the point of definition. |
| **Font fallback** | Windows TTF is attempted first; built-in ReportLab fonts are used on other platforms. |
| **Exit codes** | Distinct exit codes (0/1/2/3) allow callers and CI pipelines to distinguish error categories without parsing stderr. |

### Usage

```bash
# Auto-detect ZIP in current directory
python lattes_para_pdf.py

# Explicit ZIP
python lattes_para_pdf.py path/to/CV_<ID>.zip

# Custom output path
python lattes_para_pdf.py path/to/CV_<ID>.zip --output ~/Desktop/my_cv.pdf

# Skip pip install step (if dependencies are already installed)
python lattes_para_pdf.py path/to/CV_<ID>.zip --skip-deps
```

### Runtime Requirements

- Python ≥ 3.9
- `reportlab >= 4.0.0`
- `tqdm >= 4.65.0` *(optional: only the notebook uses tqdm; the terminal script uses plain print)*

> The script calls `pip install` automatically on startup unless `--skip-deps` is passed.

---

## test_suite.ipynb — Test Orchestrator

The notebook at `scripts/test_suite.ipynb` provides two capabilities:

### Block 1 — Version Discovery and Metadata Report

- Scans for all `v<N>/` sub-folders.
- Loads each `metadata.json` and renders a formatted report including:
  - Script name, version, created/modified dates.
  - Description, runtime, dependencies.
  - Changelog entries.
  - Known limitations.
  - Age in days since last modification.

### Block 2 — pytest Execution

- Invokes `pytest` as a subprocess against the `tests/` sub-folder of each version.
- Captures and displays stdout/stderr inline.
- Reports an overall pass/fail summary.

---

## Testing Guide

### Running tests for v1 directly

```bash
cd scripts/v1
pytest tests/ -v --tb=short
```

### Running via the test_suite.ipynb notebook

Open `scripts/test_suite.ipynb` in Jupyter and execute all cells in order.

### Test coverage (v1)

| Test class | What is tested |
|------------|----------------|
| `TestAttrHelper` | `_attr` — attribute extraction, defaults, None element, whitespace stripping |
| `TestFmtDate` | `_fmt_date` — valid 8-digit date, short string passthrough, empty string |
| `TestPeriod` | `_period` — open-ended, closed, year-only periods |
| `TestSafeEscape` | `_safe` — `&`, `<`, `>` escaping; UTF-8 passthrough |
| `TestExtractPersonal` | Field extraction, No-DADOS-GERAIS fallback |
| `TestExtractEducation` | Graduation record, empty XML |
| `TestExtractLanguages` | Language record fields, empty XML |
| `TestExtractAwards` | Award fields, empty XML |
| `TestExtractExperience` | Empty XML, deduplication logic |
| `TestExtractResearch` | Empty XML, research-line deduplication |
| `TestExtractAreas` | Empty XML, `>` separator construction |
| `TestRunPipeline` | All keys present, type contracts |
| `TestExtractXml` | Valid ZIP, ZIP without XML (exit 2), encoding declaration cleanup |
| `TestGeneratePdf` | File created, non-trivial size, valid PDF header |
| `TestIntegrationWithRealZip` | Full pipeline from real fixture ZIP *(skipped if no ZIP present)* |

---

## Contributing New Versions

1. Create `scripts/v<N>/` folder.
2. Add the Python script (entry point must be runnable as `python <script>.py`).
3. Add `metadata.json` following the schema above.
4. Add `tests/test_<script>.py` with functional pytest tests.
5. Update this `README.md` with a section describing the new version.
