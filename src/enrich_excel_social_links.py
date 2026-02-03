"""
MusicBrainz Social Links Enrichment for Excel Files.

This script enriches Excel files with social media links from MusicBrainz.
It reads artist names from the first (main) sheet and updates only the
'Social Links' sheet with data fetched from MusicBrainz.

Required columns in Social Links sheet (in order):
    Artist, Artist country, instagram_url, instagram_handle, tiktok_url,
    tiktok_handle, youtube_url, youtube_channel_id, soundcloud_url,
    soundcloud_handle, twitter_url, twitter_handle, facebook_url, website_url
"""

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd
import requests
from openpyxl import load_workbook

# MusicBrainz API configuration
MB_BASE = "https://musicbrainz.org/ws/2"
HEADERS = {"User-Agent": "catalog-metadata-qa/0.1 (contact: you@example.com)"}

# Rate limiting: MusicBrainz allows ~1 request per second
RATE_LIMIT_DELAY = 1.1

# Column order for Social Links sheet (enforced before writing)
SOCIAL_LINKS_COLUMNS = [
    "Artist",
    "Artist country",
    "instagram_url",
    "instagram_handle",
    "tiktok_url",
    "tiktok_handle",
    "youtube_url",
    "youtube_channel_id",
    "soundcloud_url",
    "soundcloud_handle",
    "twitter_url",
    "twitter_handle",
    "facebook_url",
    "website_url",
]


class MusicBrainzCache:
    """Simple file-based cache for MusicBrainz artist data."""

    def __init__(self, cache_file: str = "data/cache/mb_artist_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self):
        """Load cache from file if it exists."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._cache = {}

    def _save_cache(self):
        """Save cache to file."""
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    def get(self, artist_name: str) -> Optional[Dict]:
        """Get cached data for artist."""
        return self._cache.get(artist_name)

    def set(self, artist_name: str, data: Dict):
        """Cache data for artist."""
        self._cache[artist_name] = data
        self._save_cache()


class CheckpointManager:
    """Manages checkpointing for resumable processing."""

    def __init__(self, checkpoint_file: str = "data/cache/checkpoint.json"):
        self.checkpoint_file = Path(checkpoint_file)
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        self._checkpoint: Dict[str, Any] = {}
        self._load_checkpoint()

    def _load_checkpoint(self):
        """Load checkpoint from file if it exists."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    self._checkpoint = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._checkpoint = {}

    def _save_checkpoint(self):
        """Save checkpoint to file."""
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(self._checkpoint, f, ensure_ascii=False, indent=2)

    def get_processed_artists(self, file_key: str) -> set:
        """Get set of processed artists for a file."""
        return set(self._checkpoint.get(file_key, {}).get("processed", []))

    def mark_processed(self, file_key: str, artist_name: str):
        """Mark an artist as processed for a file."""
        if file_key not in self._checkpoint:
            self._checkpoint[file_key] = {"processed": []}
        if artist_name not in self._checkpoint[file_key]["processed"]:
            self._checkpoint[file_key]["processed"].append(artist_name)
            self._save_checkpoint()

    def clear_file(self, file_key: str):
        """Clear checkpoint for a file (used when processing is complete)."""
        if file_key in self._checkpoint:
            del self._checkpoint[file_key]
            self._save_checkpoint()


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, min_interval: float = RATE_LIMIT_DELAY):
        self.min_interval = min_interval
        self._last_call_time = 0.0

    def wait(self):
        """Wait if needed to respect rate limit."""
        now = time.time()
        elapsed = now - self._last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call_time = time.time()


# Global rate limiter instance
_rate_limiter = RateLimiter()


def search_artist(artist_name: str) -> Optional[Dict]:
    """
    Search MusicBrainz for an artist by name.

    Returns the first matching artist with their MBID.
    """
    _rate_limiter.wait()
    params = {"query": f'artist:"{artist_name}"', "fmt": "json", "limit": 1}
    try:
        r = requests.get(
            f"{MB_BASE}/artist", params=params, headers=HEADERS, timeout=30
        )
        r.raise_for_status()
        data = r.json()
        artists = data.get("artists", [])
        if artists:
            return artists[0]
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Warning: Failed to search artist '{artist_name}': {e}")
    return None


def get_artist_details(mbid: str) -> Optional[Dict]:
    """
    Get detailed artist info from MusicBrainz, including URLs.

    Args:
        mbid: MusicBrainz artist ID
    """
    _rate_limiter.wait()
    params = {"fmt": "json", "inc": "url-rels"}
    try:
        r = requests.get(
            f"{MB_BASE}/artist/{mbid}", params=params, headers=HEADERS, timeout=30
        )
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Warning: Failed to get artist details for MBID '{mbid}': {e}")
    return None


def extract_social_links(artist_data: Dict) -> Dict[str, Optional[str]]:
    """
    Extract social media links from MusicBrainz artist data.

    Returns a dict with all required social link fields.
    """
    result = {
        "instagram_url": None,
        "instagram_handle": None,
        "tiktok_url": None,
        "tiktok_handle": None,
        "youtube_url": None,
        "youtube_channel_id": None,
        "soundcloud_url": None,
        "soundcloud_handle": None,
        "twitter_url": None,
        "twitter_handle": None,
        "facebook_url": None,
        "website_url": None,
    }

    relations = artist_data.get("relations", [])
    for rel in relations:
        if rel.get("type") != "url":
            continue

        url_data = rel.get("url", {})
        url = url_data.get("resource", "")

        if not url:
            continue

        url_lower = url.lower()

        # Instagram
        if "instagram.com" in url_lower:
            result["instagram_url"] = url
            # Extract handle from URL
            parts = url.rstrip("/").split("/")
            if len(parts) > 0:
                result["instagram_handle"] = parts[-1]

        # TikTok
        elif "tiktok.com" in url_lower:
            result["tiktok_url"] = url
            parts = url.rstrip("/").split("/")
            if len(parts) > 0:
                handle = parts[-1]
                # Remove @ prefix if present
                result["tiktok_handle"] = handle.lstrip("@")

        # YouTube
        elif "youtube.com" in url_lower or "youtu.be" in url_lower:
            result["youtube_url"] = url
            # Extract channel ID if present
            if "/channel/" in url:
                parts = url.split("/channel/")
                if len(parts) > 1:
                    result["youtube_channel_id"] = parts[1].split("/")[0].split("?")[0]

        # SoundCloud
        elif "soundcloud.com" in url_lower:
            result["soundcloud_url"] = url
            parts = url.rstrip("/").split("/")
            if len(parts) > 0:
                result["soundcloud_handle"] = parts[-1]

        # Twitter/X
        elif "twitter.com" in url_lower or "x.com" in url_lower:
            result["twitter_url"] = url
            parts = url.rstrip("/").split("/")
            if len(parts) > 0:
                handle = parts[-1]
                result["twitter_handle"] = handle.lstrip("@")

        # Facebook
        elif "facebook.com" in url_lower:
            result["facebook_url"] = url

        # Official website (last resort for non-social URLs)
        elif result["website_url"] is None and rel.get("type") == "official homepage":
            result["website_url"] = url

    return result


def fetch_artist_social_data(
    artist_name: str, cache: MusicBrainzCache
) -> Dict[str, Optional[str]]:
    """
    Fetch social link data for an artist from MusicBrainz.

    Uses caching to avoid redundant API calls.
    """
    # Check cache first
    cached = cache.get(artist_name)
    if cached is not None:
        return cached

    result = {
        "Artist": artist_name,
        "Artist country": None,
        "instagram_url": None,
        "instagram_handle": None,
        "tiktok_url": None,
        "tiktok_handle": None,
        "youtube_url": None,
        "youtube_channel_id": None,
        "soundcloud_url": None,
        "soundcloud_handle": None,
        "twitter_url": None,
        "twitter_handle": None,
        "facebook_url": None,
        "website_url": None,
    }

    # Search for artist
    artist_search = search_artist(artist_name)
    if not artist_search:
        cache.set(artist_name, result)
        return result

    mbid = artist_search.get("id")
    if not mbid:
        cache.set(artist_name, result)
        return result

    # Get artist country from search result
    result["Artist country"] = artist_search.get("country") or artist_search.get(
        "area", {}
    ).get("name")

    # Get detailed info with URLs
    artist_details = get_artist_details(mbid)
    if artist_details:
        social_links = extract_social_links(artist_details)
        result.update(social_links)

    # Cache the result
    cache.set(artist_name, result)
    return result


def get_artist_names_from_excel(file_path: str) -> List[str]:
    """
    Extract unique artist names from the first sheet of an Excel file.

    Looks for an 'Artist' column in the main data sheet.
    """
    df = pd.read_excel(file_path, sheet_name=0)  # Read first sheet

    # Look for Artist column (case-insensitive)
    artist_col = None
    for col in df.columns:
        if col.lower().strip() == "artist":
            artist_col = col
            break

    if artist_col is None:
        raise ValueError(f"No 'Artist' column found in {file_path}")

    # Get unique non-null artist names
    artists = df[artist_col].dropna().unique().tolist()
    return [str(a).strip() for a in artists if str(a).strip()]


def update_social_links_sheet(
    file_path: str, social_data: List[Dict[str, Optional[str]]]
):
    """
    Update the 'Social Links' sheet in an Excel file with enriched data.

    Creates the sheet if it doesn't exist. Enforces column order.
    """
    # Load workbook
    wb = load_workbook(file_path)

    # Create or get Social Links sheet
    if "Social Links" in wb.sheetnames:
        # Remove existing sheet to replace it
        del wb["Social Links"]

    ws = wb.create_sheet("Social Links")

    # Create DataFrame with enforced column order
    df = pd.DataFrame(social_data)

    # Ensure all required columns exist
    for col in SOCIAL_LINKS_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Enforce column order
    df = df[SOCIAL_LINKS_COLUMNS]

    # Deduplicate by Artist (keep first occurrence)
    df = df.drop_duplicates(subset=["Artist"], keep="first")

    # Write header
    for col_idx, col_name in enumerate(SOCIAL_LINKS_COLUMNS, 1):
        ws.cell(row=1, column=col_idx, value=col_name)

    # Write data
    for row_idx, row in enumerate(df.itertuples(index=False), 2):
        for col_idx, value in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    # Save workbook
    wb.save(file_path)
    wb.close()


def process_excel_file(
    file_path: str,
    cache: MusicBrainzCache,
    checkpoint: CheckpointManager,
    max_workers: int = 1,  # Default to 1 for rate limiting compliance
):
    """
    Process a single Excel file with MusicBrainz enrichment.

    Args:
        file_path: Path to the Excel file
        cache: MusicBrainz cache instance
        checkpoint: Checkpoint manager instance
        max_workers: Number of parallel workers (limited by rate limiting)
    """
    print(f"\nProcessing: {file_path}")
    file_key = Path(file_path).name

    # Get artist names from main sheet
    try:
        artists = get_artist_names_from_excel(file_path)
    except ValueError as e:
        print(f"Error: {e}")
        return

    print(f"  Found {len(artists)} unique artists")

    # Check for already processed artists (from checkpoint)
    processed = checkpoint.get_processed_artists(file_key)
    artists_to_process = [a for a in artists if a not in processed]

    print(f"  {len(processed)} already processed, {len(artists_to_process)} remaining")

    # Fetch social data for each artist
    social_data = []

    # First, add already-cached data for processed artists
    for artist in artists:
        if artist in processed:
            cached = cache.get(artist)
            if cached:
                social_data.append(cached)

    # Process remaining artists
    # Note: Using sequential processing due to MusicBrainz rate limiting
    # max_workers > 1 would only help if we had multiple APIs or lifted rate limits
    if max_workers > 1:
        # Parallel execution (limited usefulness due to rate limiting)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(fetch_artist_social_data, artist, cache): artist
                for artist in artists_to_process
            }
            for future in as_completed(futures):
                artist = futures[future]
                try:
                    result = future.result()
                    social_data.append(result)
                    checkpoint.mark_processed(file_key, artist)
                    print(f"    Processed: {artist}")
                except Exception as e:
                    print(f"    Error processing '{artist}': {e}")
    else:
        # Sequential processing (respects rate limiting)
        for artist in artists_to_process:
            try:
                result = fetch_artist_social_data(artist, cache)
                social_data.append(result)
                checkpoint.mark_processed(file_key, artist)
                print(f"    Processed: {artist}")
            except Exception as e:
                print(f"    Error processing '{artist}': {e}")

    # Update Social Links sheet
    if social_data:
        update_social_links_sheet(file_path, social_data)
        print(f"  Updated 'Social Links' sheet with {len(social_data)} entries")

    # Clear checkpoint for this file (processing complete)
    checkpoint.clear_file(file_key)


def main():
    ap = argparse.ArgumentParser(
        description="Enrich Excel files with MusicBrainz social links"
    )
    ap.add_argument(
        "--files",
        nargs="+",
        default=[
            "rappers_final_enriched (michelle ivanova's conflicted copy).xlsx",
            "female_singers_final.xlsx",
            "dj_producers_final.xlsx",
        ],
        help="Excel files to process",
    )
    ap.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing the Excel files",
    )
    ap.add_argument(
        "--cache-dir",
        default="data/cache",
        help="Directory for cache files",
    )
    ap.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="Max parallel workers (1 recommended for rate limiting)",
    )
    args = ap.parse_args()

    # Resolve paths
    data_dir = Path(args.data_dir)
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Initialize cache and checkpoint manager
    cache = MusicBrainzCache(str(cache_dir / "mb_artist_cache.json"))
    checkpoint = CheckpointManager(str(cache_dir / "checkpoint.json"))

    # Process each file
    for file_name in args.files:
        file_path = data_dir / file_name
        if file_path.exists():
            process_excel_file(
                str(file_path),
                cache,
                checkpoint,
                max_workers=args.max_workers,
            )
        else:
            print(f"Warning: File not found: {file_path}")

    print("\nEnrichment complete!")


if __name__ == "__main__":
    main()
