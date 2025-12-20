# Catalog Metadata QA + Enrichment Pipeline

Pull metadata from MusicBrainz, load into SQLite, run QA checks, and enrich issues with LLM suggestions.

Built an automated music catalog metadata QA + enrichment pipeline (Python, SQLite, API integration) that detects missing fields/duplicates and generates structured remediation suggestions using an LLM-ready enrichment stage with graceful fallback behavior.

## Project Highlights
- Built an end-to-end pipeline: MusicBrainz API → JSONL → SQLite → QA rules → enriched remediation suggestions
- Uses SQL-style storage (SQLite) to support scalable downstream transformations
- Enrichment supports `--mode openai` and falls back safely to `--mode stub` to keep the pipeline reliable
- Outputs machine-readable artifacts (`qa_issues.csv`, `qa_enriched.jsonl`) for automation workflows



## What this does
End-to-end metadata QA + enrichment pipeline:
1) Pull recording metadata from MusicBrainz (JSONL)
2) Load into SQLite for queryable storage
3) Run QA checks (missing fields, duplicates)
4) Enrich issues with suggested fixes (LLM-ready; stub mode available)

## Quickstart
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

mkdir -p data/raw data/output

python src/pull_musicbrainz.py --query 'artist:"Charli XCX"' --n 50 --out data/raw/recordings.jsonl
python src/load_sqlite.py --infile data/raw/recordings.jsonl --db data/catalog.db
python src/qa_checks.py --db data/catalog.db --out data/output/qa_issues.csv
python src/llm_enrich.py --mode stub --infile data/output/qa_issues.csv --out data/output/qa_enriched.jsonl

## Run the pipeline (end-to-end)

```bash
# 1) Pull sample catalog metadata (MusicBrainz)
python src/pull_musicbrainz.py --query 'artist:"Charli XCX"' --n 50 --out data/raw/recordings.jsonl

# 2) Load into SQLite
python src/load_sqlite.py --infile data/raw/recordings.jsonl --db data/catalog.db

# 3) QA checks
python src/qa_checks.py --db data/catalog.db --out data/output/qa_issues.csv

# 4) Enrich QA issues (offline / reproducible)
python src/llm_enrich.py --mode stub --infile data/output/qa_issues.csv --out data/output/qa_enriched.jsonl

## Tech Stack
- Python (scripts + pipeline orchestration)
- MusicBrainz API (source metadata)
- SQLite (queryable storage layer)
- Rule-based QA checks (missing fields, duplicates)
- LLM-ready enrichment step (`--mode openai` with safe fallback to `--mode stub`)

## Outputs
- `data/raw/recordings.jsonl` — raw normalized pulls from MusicBrainz
- `data/catalog.db` — SQLite database of recordings
- `data/output/qa_issues.csv` — detected QA issues
- `data/output/qa_enriched.jsonl` — structured remediation suggestions per issue




