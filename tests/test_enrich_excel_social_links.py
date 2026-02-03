"""
Unit tests for enrich_excel_social_links module.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.enrich_excel_social_links import (
    SOCIAL_LINKS_COLUMNS,
    CheckpointManager,
    MusicBrainzCache,
    RateLimiter,
    extract_social_links,
    get_artist_names_from_excel,
    update_social_links_sheet,
)


class TestSocialLinksColumns:
    """Test that column order is correctly defined."""

    def test_column_order(self):
        """Verify required columns are in the correct order."""
        expected = [
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
        assert SOCIAL_LINKS_COLUMNS == expected

    def test_column_count(self):
        """Verify correct number of columns."""
        assert len(SOCIAL_LINKS_COLUMNS) == 14


class TestMusicBrainzCache:
    """Tests for MusicBrainzCache class."""

    def test_cache_set_and_get(self):
        """Test caching an artist and retrieving it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = MusicBrainzCache(f"{tmpdir}/test_cache.json")
            test_data = {"Artist": "Test Artist", "Artist country": "US"}
            cache.set("Test Artist", test_data)
            result = cache.get("Test Artist")
            assert result == test_data

    def test_cache_miss(self):
        """Test cache miss returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = MusicBrainzCache(f"{tmpdir}/test_cache.json")
            result = cache.get("Nonexistent Artist")
            assert result is None

    def test_cache_persistence(self):
        """Test that cache persists across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = f"{tmpdir}/test_cache.json"
            cache1 = MusicBrainzCache(cache_path)
            cache1.set("Artist1", {"name": "Artist1"})

            cache2 = MusicBrainzCache(cache_path)
            result = cache2.get("Artist1")
            assert result == {"name": "Artist1"}


class TestCheckpointManager:
    """Tests for CheckpointManager class."""

    def test_mark_and_get_processed(self):
        """Test marking artists as processed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint = CheckpointManager(f"{tmpdir}/checkpoint.json")
            checkpoint.mark_processed("file1.xlsx", "Artist1")
            checkpoint.mark_processed("file1.xlsx", "Artist2")

            processed = checkpoint.get_processed_artists("file1.xlsx")
            assert "Artist1" in processed
            assert "Artist2" in processed

    def test_clear_file(self):
        """Test clearing checkpoint for a file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint = CheckpointManager(f"{tmpdir}/checkpoint.json")
            checkpoint.mark_processed("file1.xlsx", "Artist1")
            checkpoint.clear_file("file1.xlsx")

            processed = checkpoint.get_processed_artists("file1.xlsx")
            assert len(processed) == 0


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_rate_limiter_initial_call(self):
        """Test that first call doesn't wait."""
        import time

        limiter = RateLimiter(min_interval=0.1)
        start = time.time()
        limiter.wait()
        elapsed = time.time() - start
        # First call should be nearly instant
        assert elapsed < 0.05


class TestExtractSocialLinks:
    """Tests for extract_social_links function."""

    def test_extract_instagram(self):
        """Test extracting Instagram URL and handle."""
        artist_data = {
            "relations": [
                {
                    "type": "url",
                    "url": {"resource": "https://instagram.com/testartist"},
                }
            ]
        }
        result = extract_social_links(artist_data)
        assert result["instagram_url"] == "https://instagram.com/testartist"
        assert result["instagram_handle"] == "testartist"

    def test_extract_youtube_channel(self):
        """Test extracting YouTube URL and channel ID."""
        artist_data = {
            "relations": [
                {
                    "type": "url",
                    "url": {"resource": "https://youtube.com/channel/UC12345"},
                }
            ]
        }
        result = extract_social_links(artist_data)
        assert result["youtube_url"] == "https://youtube.com/channel/UC12345"
        assert result["youtube_channel_id"] == "UC12345"

    def test_extract_twitter(self):
        """Test extracting Twitter URL and handle."""
        artist_data = {
            "relations": [
                {
                    "type": "url",
                    "url": {"resource": "https://twitter.com/testuser"},
                }
            ]
        }
        result = extract_social_links(artist_data)
        assert result["twitter_url"] == "https://twitter.com/testuser"
        assert result["twitter_handle"] == "testuser"

    def test_extract_x_url(self):
        """Test extracting X.com (Twitter) URL."""
        artist_data = {
            "relations": [
                {
                    "type": "url",
                    "url": {"resource": "https://x.com/testuser"},
                }
            ]
        }
        result = extract_social_links(artist_data)
        assert result["twitter_url"] == "https://x.com/testuser"
        assert result["twitter_handle"] == "testuser"

    def test_extract_empty_relations(self):
        """Test handling artist with no relations."""
        artist_data = {"relations": []}
        result = extract_social_links(artist_data)
        assert all(v is None for v in result.values())

    def test_extract_multiple_platforms(self):
        """Test extracting from multiple platforms."""
        artist_data = {
            "relations": [
                {
                    "type": "url",
                    "url": {"resource": "https://instagram.com/artist"},
                },
                {
                    "type": "url",
                    "url": {"resource": "https://facebook.com/artist"},
                },
                {
                    "type": "url",
                    "url": {"resource": "https://soundcloud.com/artist"},
                },
            ]
        }
        result = extract_social_links(artist_data)
        assert result["instagram_url"] == "https://instagram.com/artist"
        assert result["facebook_url"] == "https://facebook.com/artist"
        assert result["soundcloud_url"] == "https://soundcloud.com/artist"


class TestGetArtistNamesFromExcel:
    """Tests for get_artist_names_from_excel function."""

    def test_read_artist_names(self):
        """Test reading artist names from Excel file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = f"{tmpdir}/test.xlsx"
            df = pd.DataFrame({"Artist": ["Artist1", "Artist2", "Artist1"]})
            df.to_excel(file_path, index=False)

            artists = get_artist_names_from_excel(file_path)
            assert len(artists) == 2  # Should be unique
            assert "Artist1" in artists
            assert "Artist2" in artists

    def test_missing_artist_column(self):
        """Test error when Artist column is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = f"{tmpdir}/test.xlsx"
            df = pd.DataFrame({"Name": ["Artist1", "Artist2"]})
            df.to_excel(file_path, index=False)

            with pytest.raises(ValueError, match="No 'Artist' column found"):
                get_artist_names_from_excel(file_path)


class TestUpdateSocialLinksSheet:
    """Tests for update_social_links_sheet function."""

    def test_create_social_links_sheet(self):
        """Test creating Social Links sheet with correct columns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = f"{tmpdir}/test.xlsx"
            # Create Excel with main data sheet
            df = pd.DataFrame({"Artist": ["Artist1"]})
            df.to_excel(file_path, index=False)

            # Update with social data
            social_data = [
                {
                    "Artist": "Artist1",
                    "Artist country": "US",
                    "instagram_url": "https://instagram.com/artist1",
                }
            ]
            update_social_links_sheet(file_path, social_data)

            # Verify Social Links sheet
            result_df = pd.read_excel(file_path, sheet_name="Social Links")
            assert list(result_df.columns) == SOCIAL_LINKS_COLUMNS
            assert result_df["Artist"].iloc[0] == "Artist1"
            assert result_df["Artist country"].iloc[0] == "US"

    def test_deduplicate_by_artist(self):
        """Test that duplicate artists are removed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = f"{tmpdir}/test.xlsx"
            df = pd.DataFrame({"Artist": ["Artist1"]})
            df.to_excel(file_path, index=False)

            # Social data with duplicate artist
            social_data = [
                {"Artist": "Artist1", "Artist country": "US"},
                {"Artist": "Artist1", "Artist country": "UK"},  # Duplicate
                {"Artist": "Artist2", "Artist country": "CA"},
            ]
            update_social_links_sheet(file_path, social_data)

            result_df = pd.read_excel(file_path, sheet_name="Social Links")
            assert len(result_df) == 2  # Only 2 unique artists
            # First occurrence should be kept
            artist1_row = result_df[result_df["Artist"] == "Artist1"].iloc[0]
            assert artist1_row["Artist country"] == "US"

    def test_column_order_enforced(self):
        """Test that column order is strictly enforced."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = f"{tmpdir}/test.xlsx"
            df = pd.DataFrame({"Artist": ["Artist1"]})
            df.to_excel(file_path, index=False)

            # Social data with columns in wrong order
            social_data = [
                {
                    "website_url": "https://example.com",  # Last column first
                    "Artist": "Artist1",
                    "twitter_handle": "@artist",
                }
            ]
            update_social_links_sheet(file_path, social_data)

            result_df = pd.read_excel(file_path, sheet_name="Social Links")
            # Columns must be in the defined order
            assert list(result_df.columns) == SOCIAL_LINKS_COLUMNS
