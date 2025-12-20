import argparse
import json
import time
from pathlib import Path
import requests

MB_BASE = "https://musicbrainz.org/ws/2"
HEADERS = {"User-Agent": "catalog-metadata-qa/0.1 (contact: you@example.com)"}

def search_recordings(query: str, limit: int = 50, offset: int = 0):
    params = {"query": query, "fmt": "json", "limit": limit, "offset": offset}
    r = requests.get(f"{MB_BASE}/recording", params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def normalize(rec: dict) -> dict:
    ac = rec.get("artist-credit", [])
    artist = ac[0].get("name") if ac else None
    releases = rec.get("releases", [])
    release_title = releases[0].get("title") if releases else None
    release_date = releases[0].get("date") if releases else None

    return {
        "recording_mbid": rec.get("id"),
        "recording_title": rec.get("title"),
        "artist_name": artist,
        "length_ms": rec.get("length"),
        "first_release_title": release_title,
        "first_release_date": release_date,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True, help='e.g. artist:"Charli XCX"')
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--out", default="data/raw/recordings.jsonl")
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pulled, offset, limit = 0, 0, 50
    with out_path.open("w", encoding="utf-8") as f:
        while pulled < args.n:
            data = search_recordings(args.query, limit=limit, offset=offset)
            recs = data.get("recordings", [])
            if not recs:
                break

            for rec in recs:
                f.write(json.dumps(normalize(rec), ensure_ascii=False) + "\n")
                pulled += 1
                if pulled >= args.n:
                    break

            offset += limit
            time.sleep(1.1)

    print(f"Wrote {pulled} rows -> {out_path}")

if __name__ == "__main__":
    main()