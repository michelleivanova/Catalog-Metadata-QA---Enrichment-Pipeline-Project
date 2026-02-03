# Catalog Metadata QA + Enrichment Pipeline

End-to-end automation pipeline for music catalog metadata quality checks and remediation suggestions.

**Summary:** Built an automated music catalog metadata QA + enrichment pipeline (Python, SQLite, API integration) that detects missing fields/duplicates and generates structured remediation suggestions via an LLM-ready enrichment stage with graceful fallback behavior.

## Project Highlights
- End-to-end pipeline: **MusicBrainz API → JSONL → SQLite → QA rules → enriched remediation suggestions**
- Uses **SQLite** as a lightweight SQL-style storage layer for scalable transformations
- Enrichment supports `--mode openai` and falls back safely to `--mode stub` to keep the pipeline reliable
- Outputs machine-readable artifacts (`qa_issues.csv`, `qa_enriched.jsonl`) designed for automation workflows
- **Excel enrichment**: Updates Excel files' "Social Links" sheet with MusicBrainz social media data
- Includes a `Makefile` runner and a `pytest` smoke test

## What this does
1. Pull recording metadata from MusicBrainz (JSONL)
2. Load into SQLite for queryable storage
3. Run QA checks (missing fields, duplicates)
4. Enrich issues with suggested fixes (LLM-ready; stub mode available)
5. **NEW:** Enrich Excel files with MusicBrainz social links

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

## Excel Social Links Enrichment

Enrich Excel files with MusicBrainz social media data. This updates only the "Social Links" sheet without altering the main data sheet.

```bash
# Place Excel files in data/ directory, then run:
python src/enrich_excel_social_links.py --data-dir data

# Or specify files directly:
python src/enrich_excel_social_links.py --files file1.xlsx file2.xlsx --data-dir /path/to/files
```

### Default files processed:
- `rappers_final_enriched (michelle ivanova's conflicted copy).xlsx`
- `female_singers_final.xlsx`
- `dj_producers_final.xlsx`

### Social Links sheet columns (in order):
1. Artist
2. Artist country
3. instagram_url
4. instagram_handle
5. tiktok_url
6. tiktok_handle
7. youtube_url
8. youtube_channel_id
9. soundcloud_url
10. soundcloud_handle
11. twitter_url
12. twitter_handle
13. facebook_url
14. website_url

### Features:
- **Rate limiting**: Respects MusicBrainz API rate limits (~1 request/second)
- **Checkpointing**: Resume processing if interrupted
- **Caching**: Avoids redundant API calls for the same artists
- **Deduplication**: Uses Artist as unique key (first occurrence kept)

## One-command run
```bash
make all

# For Excel enrichment:
make enrich-excel
