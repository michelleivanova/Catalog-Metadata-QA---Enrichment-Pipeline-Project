# Catalog Metadata QA + Enrichment Pipeline

End-to-end automation pipeline for music catalog metadata quality checks and remediation suggestions.

**Summary (resume-style):** Built an automated music catalog metadata QA + enrichment pipeline (Python, SQLite, API integration) that detects missing fields/duplicates and generates structured remediation suggestions via an LLM-ready enrichment stage with graceful fallback behavior.

## Project Highlights
- End-to-end pipeline: **MusicBrainz API → JSONL → SQLite → QA rules → enriched remediation suggestions**
- Uses **SQLite** as a lightweight SQL-style storage layer for scalable transformations
- Enrichment supports `--mode openai` and falls back safely to `--mode stub` to keep the pipeline reliable
- Outputs machine-readable artifacts (`qa_issues.csv`, `qa_enriched.jsonl`) designed for automation workflows
- Includes a `Makefile` runner and a `pytest` smoke test

## What this does
1. Pull recording metadata from MusicBrainz (JSONL)
2. Load into SQLite for queryable storage
3. Run QA checks (missing fields, duplicates)
4. Enrich issues with suggested fixes (LLM-ready; stub mode available)

## Run the pipeline (end-to-end)

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

mkdir -p data/raw data/output

# 1) Pull sample catalog metadata (MusicBrainz)
python src/pull_musicbrainz.py --query 'artist:"Charli XCX"' --n 50 --out data/raw/recordings.jsonl

# 2) Load into SQLite
python src/load_sqlite.py --infile data/raw/recordings.jsonl --db data/catalog.db

# 3) QA checks
python src/qa_checks.py --db data/catalog.db --out data/output/qa_issues.csv

# 4) Enrich QA issues (offline / reproducible)
python src/llm_enrich.py --mode stub --infile data/output/qa_issues.csv --out data/output/qa_enriched.jsonl

```