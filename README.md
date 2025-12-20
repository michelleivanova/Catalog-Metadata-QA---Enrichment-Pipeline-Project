# Catalog Metadata QA + Enrichment Pipeline

Pull metadata from MusicBrainz, load into SQLite, run QA checks, and enrich issues with LLM suggestions.

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

