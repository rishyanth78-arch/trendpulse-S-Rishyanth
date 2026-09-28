"""
TrendPulse - Task 2: Data Processing
Reads raw_trends.json, cleans and normalises each source, then writes
cleaned_trends.json ready for analysis.

Cleaning steps per source
--------------------------
GitHub  : strip whitespace, parse star/fork counts to int, drop duplicates
Wikipedia: strip whitespace, drop Main_Page / special pages, deduplicate titles
Reddit  : strip whitespace, parse score/comments to int, convert UTC timestamp,
          remove deleted/removed authors, drop duplicates by URL
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------
INPUT_FILE = "raw_trends.json"
OUTPUT_FILE = "cleaned_trends.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_number(value: str | int | float) -> int:
    """
    Convert a string like '1,234', '4.5k', '12,345 stars' to an integer.
    Returns 0 if parsing fails.
    """
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().lower()
    # Remove commas and non-numeric suffixes except 'k'/'m'
    text = re.sub(r"[^\d.km]", "", text)
    if not text:
        return 0
    try:
        if text.endswith("k"):
            return int(float(text[:-1]) * 1_000)
        if text.endswith("m"):
            return int(float(text[:-1]) * 1_000_000)
        return int(float(text))
    except ValueError:
        return 0


def _clean_text(value: str) -> str:
    """Normalise whitespace and strip leading/trailing spaces."""
    return re.sub(r"\s+", " ", str(value)).strip()


def _utc_timestamp_to_iso(ts: int | float) -> str:
    """Convert a Unix UTC timestamp to an ISO-8601 string."""
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except (ValueError, OSError):
        return ""


# ---------------------------------------------------------------------------
# Per-source cleaners
# ---------------------------------------------------------------------------
def clean_github(records: list[dict]) -> list[dict]:
    """Clean GitHub trending records."""
    seen: set[str] = set()
    cleaned: list[dict] = []

    for rec in records:
        repo = _clean_text(rec.get("repo", ""))
        if not repo or repo in seen:
            continue
        seen.add(repo)

        cleaned.append(
            {
                "source": "github_trending",
                "repo": repo,
                "description": _clean_text(rec.get("description", "")),
                "language": _clean_text(rec.get("language", "Unknown")),
                "stars_today": _parse_number(rec.get("stars_today", 0)),
                "total_stars": _parse_number(rec.get("total_stars", 0)),
                "forks": _parse_number(rec.get("forks", 0)),
                "url": _clean_text(rec.get("url", "")),
            }
        )

    log.info("GitHub: %d -> %d records after cleaning.", len(records), len(cleaned))
    return cleaned


def clean_wikipedia(records: list[dict]) -> list[dict]:
    """Clean Wikipedia trending records."""
    seen: set[str] = set()
    cleaned: list[dict] = []
    skip_prefixes = ("Special:", "Main Page", "Wikipedia:", "File:", "Help:")

    for rec in records:
        title = _clean_text(rec.get("title", ""))
        if not title:
            continue
        if any(title.startswith(p) for p in skip_prefixes):
            continue
        if title in seen:
            continue
        seen.add(title)

        cleaned.append(
            {
                "source": "wikipedia_trending",
                "title": title,
                "rank": int(rec.get("rank") or 0),
                "views": int(rec.get("views") or 0),
                "url": _clean_text(rec.get("url", "")),
            }
        )

    log.info(
        "Wikipedia: %d -> %d records after cleaning.", len(records), len(cleaned)
    )
    return cleaned


def clean_reddit(records: list[dict]) -> list[dict]:
    """Clean Reddit trending records."""
    seen_urls: set[str] = set()
    cleaned: list[dict] = []
    deleted_authors = {"[deleted]", "[removed]", ""}

    for rec in records:
        url = _clean_text(rec.get("url", ""))
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        author = _clean_text(rec.get("author", ""))
        if author in deleted_authors:
            author = "unknown"

        title = _clean_text(rec.get("title", ""))
        if not title:
            continue

        cleaned.append(
            {
                "source": "reddit_trending",
                "title": title,
                "subreddit": _clean_text(rec.get("subreddit", "")),
                "score": _parse_number(rec.get("score", 0)),
                "upvote_ratio": round(float(rec.get("upvote_ratio") or 0.0), 4),
                "num_comments": _parse_number(rec.get("num_comments", 0)),
                "author": author,
                "url": url,
                "created_at": _utc_timestamp_to_iso(rec.get("created_utc", 0)),
            }
        )

    log.info("Reddit: %d -> %d records after cleaning.", len(records), len(cleaned))
    return cleaned


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
CLEANERS = {
    "github_trending": clean_github,
    "wikipedia_trending": clean_wikipedia,
    "reddit_trending": clean_reddit,
}


def process(input_path: str = INPUT_FILE, output_path: str = OUTPUT_FILE) -> dict:
    """Load raw data, apply cleaners, and return the cleaned payload."""
    raw_path = Path(input_path)
    if not raw_path.exists():
        raise FileNotFoundError(
            f"'{input_path}' not found. Run task1_data_collection.py first."
        )

    log.info("Loading raw data from %s …", input_path)
    with open(raw_path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    sources_raw: dict = raw.get("sources", {})
    cleaned_sources: dict = {}
    total_before, total_after = 0, 0

    for source_name, records in sources_raw.items():
        cleaner = CLEANERS.get(source_name)
        if cleaner is None:
            log.warning("No cleaner defined for source '%s', skipping.", source_name)
            cleaned_sources[source_name] = records
            continue

        total_before += len(records)
        cleaned = cleaner(records)
        total_after += len(cleaned)
        cleaned_sources[source_name] = cleaned

    payload = {
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "original_collected_at": raw.get("collected_at", ""),
        "record_counts": {
            src: len(recs) for src, recs in cleaned_sources.items()
        },
        "total_records_before": total_before,
        "total_records_after": total_after,
        "records_dropped": total_before - total_after,
        "sources": cleaned_sources,
    }

    log.info(
        "Processing complete. %d -> %d records (%d dropped).",
        total_before,
        total_after,
        total_before - total_after,
    )
    return payload


def save(data: dict, filepath: str = OUTPUT_FILE) -> None:
    """Write cleaned data to JSON."""
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    log.info("Cleaned data saved to %s", filepath)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    result = process()
    save(result)

    print("\n=== Processing Summary ===")
    print(f"  Records before cleaning : {result['total_records_before']}")
    print(f"  Records after  cleaning : {result['total_records_after']}")
    print(f"  Records dropped         : {result['records_dropped']}")
    print("\n  Per-source counts:")
    for src, count in result["record_counts"].items():
        print(f"    {src}: {count}")
    print(f"\nCleaned data saved to '{OUTPUT_FILE}'")
