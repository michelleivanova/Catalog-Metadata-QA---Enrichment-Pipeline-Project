pull:
	python src/pull_musicbrainz.py --query 'artist:"Charli XCX"' --n 50 --out data/raw/recordings.jsonl

load:
	python src/load_sqlite.py --infile data/raw/recordings.jsonl --db data/catalog.db

qa:
	python src/qa_checks.py --db data/catalog.db --out data/output/qa_issues.csv

enrich:
	python src/llm_enrich.py --mode stub --infile data/output/qa_issues.csv --out data/output/qa_enriched.jsonl

enrich-excel:
	python src/enrich_excel_social_links.py --data-dir data

all: pull load qa enrich
