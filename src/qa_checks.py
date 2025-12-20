import argparse
import sqlite3
from pathlib import Path
import pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/catalog.db")
    ap.add_argument("--out", default="data/output/qa_issues.csv")
    args = ap.parse_args()

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(args.db)
    df = pd.read_sql_query("SELECT * FROM recordings", conn)
    conn.close()

    issues = []

    # 1) Missing critical fields
    for _, r in df.iterrows():
        if not r["artist_name"]:
            issues.append(("missing_artist_name", r["recording_mbid"], r["recording_title"]))
        if not r["recording_title"]:
            issues.append(("missing_recording_title", r["recording_mbid"], None))
        if not r["first_release_title"]:
            issues.append(("missing_release_title", r["recording_mbid"], r["recording_title"]))
        if r["length_ms"] is None:
            issues.append(("missing_length_ms", r["recording_mbid"], r["recording_title"]))

    # 2) Duplicate title within artist
    dup = (
        df.groupby(["artist_name", "recording_title"])
          .size()
          .reset_index(name="count")
    )
    dup = dup[(dup["artist_name"].notna()) & (dup["recording_title"].notna()) & (dup["count"] > 1)]
    for _, d in dup.iterrows():
        issues.append(("duplicate_title_artist", None, f'{d["artist_name"]} - {d["recording_title"]} (x{d["count"]})'))

    out_df = pd.DataFrame(issues, columns=["issue_type", "recording_mbid", "detail"])
    out_df.to_csv(args.out, index=False)
    print(f"Found {len(out_df)} issues -> {args.out}")

if __name__ == "__main__":
    main()