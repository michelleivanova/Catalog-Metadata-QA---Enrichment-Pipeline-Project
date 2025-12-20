import argparse
import json
import sqlite3
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", required=True, help="Path to JSONL file")
    ap.add_argument("--db", default="data/catalog.db", help="SQLite db path")
    args = ap.parse_args()

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS recordings (
        recording_mbid TEXT PRIMARY KEY,
        recording_title TEXT,
        artist_name TEXT,
        length_ms INTEGER,
        first_release_title TEXT,
        first_release_date TEXT
    )
    """)

    inserted = 0
    with open(args.infile, "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            cur.execute("""
            INSERT OR REPLACE INTO recordings
            (recording_mbid, recording_title, artist_name, length_ms, first_release_title, first_release_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                row.get("recording_mbid"),
                row.get("recording_title"),
                row.get("artist_name"),
                row.get("length_ms"),
                row.get("first_release_title"),
                row.get("first_release_date"),
            ))
            inserted += 1

    conn.commit()
    conn.close()
    print(f"Loaded {inserted} rows into {db_path}")

if __name__ == "__main__":
    main()
