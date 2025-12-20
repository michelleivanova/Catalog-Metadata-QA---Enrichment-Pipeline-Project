import argparse
import json
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


def build_prompt(issue_type: str, detail: str) -> str:
    return f"""
You are a music metadata QA assistant.

Return ONLY valid JSON with keys:
- suggested_fix (string)
- confidence ("low"|"medium"|"high")
- notes (string)

Issue type: {issue_type}
Detail: {detail}
""".strip()


def enrich_stub(issue_type: str, detail: str) -> dict:
    if issue_type == "missing_release_title":
        return {
            "suggested_fix": "Re-query MusicBrainz for releases linked to this recording MBID; if none, flag for manual review.",
            "confidence": "medium",
            "notes": "Recording may be missing release relationships or the pull did not include enough relationships."
        }
    if issue_type == "duplicate_title_artist":
        return {
            "suggested_fix": "Check if entries are distinct versions (remix/live/clean). If identical, dedupe by MBID and keep earliest release date.",
            "confidence": "high",
            "notes": "Artist+title duplicates often represent alternate versions; MBID/release fields help disambiguate."
        }
    return {
        "suggested_fix": "Review record and apply standard normalization rules.",
        "confidence": "low",
        "notes": "Stub mode."
    }


def enrich_openai(model: str, prompt: str) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    resp = client.responses.create(
        model=model,
        input=prompt,
        temperature=0.2
    )
    text = resp.output_text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"suggested_fix": None, "confidence": "low", "notes": f"Non-JSON output: {text[:200]}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", default="data/output/qa_issues.csv")
    ap.add_argument("--out", default="data/output/qa_enriched.jsonl")
    ap.add_argument("--mode", choices=["stub", "openai"], default="stub")
    ap.add_argument("--model", default="gpt-4.1-mini")
    args = ap.parse_args()

    load_dotenv()

    df = pd.read_csv(args.infile)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    with open(args.out, "w", encoding="utf-8") as f:
        for _, r in df.iterrows():
            issue_type = str(r["issue_type"])
            detail = "" if pd.isna(r["detail"]) else str(r["detail"])

            if args.mode == "openai":
                prompt = build_prompt(issue_type, detail)
                enriched = enrich_openai(args.model, prompt)
            else:
                enriched = enrich_stub(issue_type, detail)

            out_row = {
                "issue_type": issue_type,
                "recording_mbid": None if pd.isna(r.get("recording_mbid")) else r.get("recording_mbid"),
                "detail": detail,
                **enriched
            }
            f.write(json.dumps(out_row, ensure_ascii=False) + "\n")

    print(f"Wrote {len(df)} enriched rows -> {args.out} (mode={args.mode})")


if __name__ == "__main__":
    main()