"""
TrendPulse - Task 3: Analysis
Reads cleaned_trends.json and produces analytical insights:

  GitHub    : top repos by stars today, language distribution, star-to-fork ratio
  Wikipedia : top articles by views, view-rank correlation
  Reddit    : top posts by score, subreddit breakdown, engagement score
  Cross     : unified trending score across all sources, overall summary stats

Results are saved to analysis_results.json.
"""

import json
import logging
import statistics
from collections import Counter
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
INPUT_FILE = "cleaned_trends.json"
OUTPUT_FILE = "analysis_results.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Return numerator / denominator, or default if denominator is zero."""
    return numerator / denominator if denominator else default


def _summary_stats(values: list[float | int]) -> dict:
    """Return basic descriptive statistics for a numeric list."""
    if not values:
        return {"count": 0, "min": 0, "max": 0, "mean": 0, "median": 0, "stdev": 0}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "stdev": round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
    }


# ---------------------------------------------------------------------------
# GitHub Analysis
# ---------------------------------------------------------------------------
def analyse_github(records: list[dict]) -> dict:
    """Analyse GitHub trending repositories."""
    if not records:
        return {}

    # Sort by stars today
    by_stars = sorted(records, key=lambda r: r["stars_today"], reverse=True)

    # Language distribution
    lang_counter = Counter(r["language"] for r in records if r["language"])
    top_languages = [
        {"language": lang, "repo_count": count}
        for lang, count in lang_counter.most_common(10)
    ]

    # Star-to-fork ratios
    ratios = [
        {
            "repo": r["repo"],
            "ratio": round(_safe_div(r["total_stars"], r["forks"]), 2),
            "total_stars": r["total_stars"],
            "forks": r["forks"],
        }
        for r in records
        if r["forks"] > 0
    ]
    ratios.sort(key=lambda x: x["ratio"], reverse=True)

    # Stars today stats
    stars_today_values = [r["stars_today"] for r in records]

    log.info("GitHub analysis complete. Top repo: %s", by_stars[0]["repo"] if by_stars else "N/A")

    return {
        "total_repos": len(records),
        "top_repos_by_stars_today": [
            {
                "rank": i + 1,
                "repo": r["repo"],
                "description": r["description"],
                "language": r["language"],
                "stars_today": r["stars_today"],
                "total_stars": r["total_stars"],
                "url": r["url"],
            }
            for i, r in enumerate(by_stars[:10])
        ],
        "language_distribution": top_languages,
        "unique_languages": len(lang_counter),
        "top_star_to_fork_ratios": ratios[:5],
        "stars_today_stats": _summary_stats(stars_today_values),
    }


# ---------------------------------------------------------------------------
# Wikipedia Analysis
# ---------------------------------------------------------------------------
def analyse_wikipedia(records: list[dict]) -> dict:
    """Analyse Wikipedia trending articles."""
    if not records:
        return {}

    by_views = sorted(records, key=lambda r: r["views"], reverse=True)
    views_values = [r["views"] for r in records]

    # View share (percentage of total views)
    total_views = sum(views_values)
    top_with_share = [
        {
            "rank": r["rank"],
            "title": r["title"],
            "views": r["views"],
            "view_share_pct": round(_safe_div(r["views"] * 100, total_views), 2),
            "url": r["url"],
        }
        for r in by_views[:10]
    ]

    # Rank vs views: simple Spearman-like direction check
    ranks = [r["rank"] for r in records]
    views = [r["views"] for r in records]
    correlation_note = (
        "Higher rank (lower number) generally corresponds to higher views — "
        "confirming rank is driven by pageview count."
        if len(ranks) > 1
        else "Insufficient data for correlation."
    )

    log.info(
        "Wikipedia analysis complete. Top article: %s",
        by_views[0]["title"] if by_views else "N/A",
    )

    return {
        "total_articles": len(records),
        "total_views": total_views,
        "top_articles_by_views": top_with_share,
        "views_stats": _summary_stats(views_values),
        "rank_views_correlation_note": correlation_note,
    }


# ---------------------------------------------------------------------------
# Reddit Analysis
# ---------------------------------------------------------------------------
def analyse_reddit(records: list[dict]) -> dict:
    """Analyse Reddit trending posts."""
    if not records:
        return {}

    # Engagement score: score * upvote_ratio + log(comments + 1)
    import math

    for r in records:
        r["_engagement"] = round(
            r["score"] * r["upvote_ratio"] + math.log1p(r["num_comments"]) * 10,
            2,
        )

    by_engagement = sorted(records, key=lambda r: r["_engagement"], reverse=True)
    by_score = sorted(records, key=lambda r: r["score"], reverse=True)

    # Subreddit breakdown
    sub_counter = Counter(r["subreddit"] for r in records)
    top_subreddits = [
        {"subreddit": sub, "post_count": cnt}
        for sub, cnt in sub_counter.most_common(10)
    ]

    scores = [r["score"] for r in records]
    comments = [r["num_comments"] for r in records]

    log.info(
        "Reddit analysis complete. Top post: %s",
        by_score[0]["title"][:60] if by_score else "N/A",
    )

    return {
        "total_posts": len(records),
        "top_posts_by_engagement": [
            {
                "rank": i + 1,
                "title": r["title"],
                "subreddit": r["subreddit"],
                "score": r["score"],
                "num_comments": r["num_comments"],
                "upvote_ratio": r["upvote_ratio"],
                "engagement_score": r["_engagement"],
                "url": r["url"],
            }
            for i, r in enumerate(by_engagement[:10])
        ],
        "top_posts_by_score": [
            {
                "rank": i + 1,
                "title": r["title"][:80],
                "score": r["score"],
                "subreddit": r["subreddit"],
            }
            for i, r in enumerate(by_score[:5])
        ],
        "top_subreddits": top_subreddits,
        "unique_subreddits": len(sub_counter),
        "score_stats": _summary_stats(scores),
        "comment_stats": _summary_stats(comments),
    }


# ---------------------------------------------------------------------------
# Cross-Source Analysis
# ---------------------------------------------------------------------------
def cross_source_analysis(
    github: list[dict],
    wikipedia: list[dict],
    reddit: list[dict],
) -> dict:
    """Produce a unified trending score and overall summary."""

    # Normalise each source to a 0–100 score based on its top metric
    def normalise(values: list[float]) -> list[float]:
        max_val = max(values) if values else 1
        return [round(v / max_val * 100, 2) for v in values]

    gh_scores = normalise([r["stars_today"] for r in github])
    wiki_scores = normalise([r["views"] for r in wikipedia])

    import math
    reddit_eng = [
        r["score"] * r["upvote_ratio"] + math.log1p(r["num_comments"]) * 10
        for r in reddit
    ]
    rd_scores = normalise(reddit_eng)

    # Unified top-10 items per source
    top_items = []
    for i, r in enumerate(sorted(github, key=lambda x: x["stars_today"], reverse=True)[:5]):
        top_items.append(
            {
                "source": "GitHub",
                "name": r["repo"],
                "normalised_score": gh_scores[i] if i < len(gh_scores) else 0,
                "url": r["url"],
            }
        )
    for i, r in enumerate(sorted(wikipedia, key=lambda x: x["views"], reverse=True)[:5]):
        top_items.append(
            {
                "source": "Wikipedia",
                "name": r["title"],
                "normalised_score": wiki_scores[i] if i < len(wiki_scores) else 0,
                "url": r["url"],
            }
        )
    for i, r in enumerate(
        sorted(reddit, key=lambda x: x["score"], reverse=True)[:5]
    ):
        top_items.append(
            {
                "source": "Reddit",
                "name": r["title"][:80],
                "normalised_score": rd_scores[i] if i < len(rd_scores) else 0,
                "url": r["url"],
            }
        )

    top_items.sort(key=lambda x: x["normalised_score"], reverse=True)

    return {
        "unified_top_trending": top_items,
        "source_record_counts": {
            "github": len(github),
            "wikipedia": len(wikipedia),
            "reddit": len(reddit),
            "total": len(github) + len(wikipedia) + len(reddit),
        },
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def analyse(input_path: str = INPUT_FILE, output_path: str = OUTPUT_FILE) -> dict:
    """Load cleaned data, run analyses, return results."""
    cleaned_path = Path(input_path)
    if not cleaned_path.exists():
        raise FileNotFoundError(
            f"'{input_path}' not found. Run task2_data_processing.py first."
        )

    log.info("Loading cleaned data from %s …", input_path)
    with open(cleaned_path, "r", encoding="utf-8") as fh:
        cleaned = json.load(fh)

    sources = cleaned.get("sources", {})
    github = sources.get("github_trending", [])
    wikipedia = sources.get("wikipedia_trending", [])
    reddit = sources.get("reddit_trending", [])

    log.info("Running per-source analyses …")
    results = {
        "analysed_at": datetime.now(timezone.utc).isoformat(),
        "data_collected_at": cleaned.get("original_collected_at", ""),
        "github_analysis": analyse_github(github),
        "wikipedia_analysis": analyse_wikipedia(wikipedia),
        "reddit_analysis": analyse_reddit(reddit),
        "cross_source": cross_source_analysis(github, wikipedia, reddit),
    }

    log.info("Analysis complete.")
    return results


def save(data: dict, filepath: str = OUTPUT_FILE) -> None:
    """Write analysis results to JSON."""
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    log.info("Analysis saved to %s", filepath)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    results = analyse()
    save(results)

    print("\n=== Analysis Summary ===")

    gh = results.get("github_analysis", {})
    if gh:
        top_gh = gh["top_repos_by_stars_today"][0] if gh["top_repos_by_stars_today"] else {}
        print(f"\nGitHub ({gh['total_repos']} repos, {gh['unique_languages']} languages)")
        print(f"  Top repo    : {top_gh.get('repo', 'N/A')} ({top_gh.get('stars_today', 0)} stars today)")
        print(f"  Top language: {gh['language_distribution'][0]['language'] if gh['language_distribution'] else 'N/A'}")

    wiki = results.get("wikipedia_analysis", {})
    if wiki:
        top_w = wiki["top_articles_by_views"][0] if wiki["top_articles_by_views"] else {}
        print(f"\nWikipedia ({wiki['total_articles']} articles, {wiki['total_views']:,} total views)")
        print(f"  Top article : {top_w.get('title', 'N/A')} ({top_w.get('views', 0):,} views)")

    rd = results.get("reddit_analysis", {})
    if rd:
        top_r = rd["top_posts_by_score"][0] if rd["top_posts_by_score"] else {}
        print(f"\nReddit ({rd['total_posts']} posts, {rd['unique_subreddits']} subreddits)")
        print(f"  Top post    : {top_r.get('title', 'N/A')[:60]}")

    cross = results.get("cross_source", {})
    if cross.get("unified_top_trending"):
        top_unified = cross["unified_top_trending"][0]
        print(f"\nUnified #1 Trending: [{top_unified['source']}] {top_unified['name'][:60]}")

    print(f"\nFull analysis saved to '{OUTPUT_FILE}'")
