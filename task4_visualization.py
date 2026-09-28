"""
TrendPulse - Task 4: Visualization
Reads analysis_results.json and produces a set of charts saved as PNG files,
plus a self-contained HTML dashboard (trendpulse_dashboard.html).

Charts generated
-----------------
1. github_top_repos.png        – Horizontal bar: top GitHub repos by stars today
2. github_languages.png        – Pie chart: language distribution
3. wikipedia_top_articles.png  – Horizontal bar: top Wikipedia articles by views
4. reddit_top_posts.png        – Horizontal bar: top Reddit posts by engagement score
5. reddit_subreddits.png       – Bar chart: top subreddits by post count
6. cross_source_trending.png   – Bubble/scatter: unified trending scores across sources
7. trendpulse_dashboard.html   – All charts embedded in a single HTML page
"""

import base64
import json
import logging
import textwrap
from io import BytesIO
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — works without a display
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

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
INPUT_FILE = "analysis_results.json"
OUTPUT_DIR = Path("charts")

# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------
PALETTE = {
    "github": "#238636",
    "wikipedia": "#3366CC",
    "reddit": "#FF4500",
    "accent": "#F0A500",
    "bg": "#0D1117",
    "fg": "#C9D1D9",
    "grid": "#21262D",
}

plt.rcParams.update(
    {
        "figure.facecolor": PALETTE["bg"],
        "axes.facecolor": PALETTE["bg"],
        "axes.edgecolor": PALETTE["grid"],
        "axes.labelcolor": PALETTE["fg"],
        "xtick.color": PALETTE["fg"],
        "ytick.color": PALETTE["fg"],
        "text.color": PALETTE["fg"],
        "grid.color": PALETTE["grid"],
        "grid.linestyle": "--",
        "grid.alpha": 0.6,
        "font.family": "DejaVu Sans",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _save(fig: plt.Figure, filename: str) -> Path:
    """Save figure to OUTPUT_DIR and return path."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / filename
    fig.savefig(path, bbox_inches="tight", dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    log.info("Saved %s", path)
    return path


def _fig_to_b64(path: Path) -> str:
    """Read a PNG and return a base64 data URI for embedding in HTML."""
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode()


def _wrap_labels(labels: list[str], width: int = 28) -> list[str]:
    """Wrap long label strings to fit chart axes."""
    return ["\n".join(textwrap.wrap(lbl, width)) for lbl in labels]


# ---------------------------------------------------------------------------
# Chart 1 – GitHub Top Repos by Stars Today
# ---------------------------------------------------------------------------
def chart_github_repos(data: dict) -> Path:
    repos = data.get("top_repos_by_stars_today", [])[:10]
    if not repos:
        log.warning("No GitHub repo data to plot.")
        return None

    names = _wrap_labels([r["repo"].split("/")[-1] for r in repos])
    stars = [r["stars_today"] for r in repos]
    langs = [r["language"] for r in repos]

    # Colour bars by language (top 5 get distinct colours, rest grey)
    from collections import Counter
    top_langs = [l for l, _ in Counter(langs).most_common(5)]
    cmap = plt.cm.get_cmap("tab10")
    bar_colours = [
        cmap(top_langs.index(l) / 10) if l in top_langs else "#555"
        for l in langs
    ]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(names[::-1], stars[::-1], color=bar_colours[::-1], edgecolor="none")

    # Value labels
    for bar, val in zip(bars, stars[::-1]):
        ax.text(
            bar.get_width() + max(stars) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,}",
            va="center",
            fontsize=8,
            color=PALETTE["fg"],
        )

    ax.set_xlabel("Stars gained today")
    ax.set_title("GitHub — Top Repos by Stars Today", fontsize=13, fontweight="bold",
                 color=PALETTE["github"], pad=12)
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legend
    patches = [
        mpatches.Patch(color=cmap(i / 10), label=l)
        for i, l in enumerate(top_langs)
    ]
    ax.legend(handles=patches, loc="lower right", fontsize=7,
              facecolor=PALETTE["bg"], edgecolor=PALETTE["grid"])

    fig.tight_layout()
    return _save(fig, "github_top_repos.png")


# ---------------------------------------------------------------------------
# Chart 2 – GitHub Language Distribution (Pie)
# ---------------------------------------------------------------------------
def chart_github_languages(data: dict) -> Path:
    langs_data = data.get("language_distribution", [])[:8]
    if not langs_data:
        log.warning("No language distribution data.")
        return None

    labels = [d["language"] for d in langs_data]
    counts = [d["repo_count"] for d in langs_data]

    fig, ax = plt.subplots(figsize=(7, 7))
    wedge_props = {"edgecolor": PALETTE["bg"], "linewidth": 2}
    wedges, texts, autotexts = ax.pie(
        counts,
        labels=labels,
        autopct="%1.1f%%",
        startangle=140,
        wedgeprops=wedge_props,
        colors=plt.cm.tab10.colors[: len(labels)],
    )
    for at in autotexts:
        at.set_fontsize(8)
    for t in texts:
        t.set_fontsize(9)

    ax.set_title(
        "GitHub — Language Distribution", fontsize=13, fontweight="bold",
        color=PALETTE["github"], pad=16,
    )
    fig.tight_layout()
    return _save(fig, "github_languages.png")


# ---------------------------------------------------------------------------
# Chart 3 – Wikipedia Top Articles by Views
# ---------------------------------------------------------------------------
def chart_wikipedia_articles(data: dict) -> Path:
    articles = data.get("top_articles_by_views", [])[:10]
    if not articles:
        log.warning("No Wikipedia article data.")
        return None

    titles = _wrap_labels([a["title"] for a in articles])
    views = [a["views"] for a in articles]
    shares = [a["view_share_pct"] for a in articles]

    fig, ax1 = plt.subplots(figsize=(11, 6))
    ax2 = ax1.twiny()

    y = range(len(titles))
    ax1.barh(list(y)[::-1], views, color=PALETTE["wikipedia"], alpha=0.85, edgecolor="none",
             label="Views")
    ax2.plot(shares[::-1], list(y)[::-1], "o--", color=PALETTE["accent"],
             markersize=6, linewidth=1.5, label="Share %")

    ax1.set_xlabel("Page Views", color=PALETTE["wikipedia"])
    ax2.set_xlabel("View Share (%)", color=PALETTE["accent"])
    ax1.set_yticks(list(y)[::-1])
    ax1.set_yticklabels(titles[::-1], fontsize=8)
    ax1.set_title(
        "Wikipedia — Top Articles by Views", fontsize=13, fontweight="bold",
        color=PALETTE["wikipedia"], pad=28,
    )
    ax1.xaxis.grid(True)
    ax1.set_axisbelow(True)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="lower right", fontsize=8,
               facecolor=PALETTE["bg"], edgecolor=PALETTE["grid"])

    fig.tight_layout()
    return _save(fig, "wikipedia_top_articles.png")


# ---------------------------------------------------------------------------
# Chart 4 – Reddit Top Posts by Engagement Score
# ---------------------------------------------------------------------------
def chart_reddit_posts(data: dict) -> Path:
    posts = data.get("top_posts_by_engagement", [])[:10]
    if not posts:
        log.warning("No Reddit post data.")
        return None

    titles = _wrap_labels([p["title"] for p in posts], width=35)
    engagement = [p["engagement_score"] for p in posts]
    scores = [p["score"] for p in posts]

    # Colour intensity by score
    norm_scores = np.array(scores, dtype=float)
    if norm_scores.max() > 0:
        norm_scores = norm_scores / norm_scores.max()
    colours = [plt.cm.YlOrRd(0.3 + 0.7 * v) for v in norm_scores]

    fig, ax = plt.subplots(figsize=(11, 6))
    bars = ax.barh(titles[::-1], engagement[::-1], color=colours[::-1], edgecolor="none")

    for bar, val in zip(bars, engagement[::-1]):
        ax.text(
            bar.get_width() + max(engagement) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,.0f}",
            va="center",
            fontsize=8,
            color=PALETTE["fg"],
        )

    ax.set_xlabel("Engagement Score")
    ax.set_title("Reddit — Top Posts by Engagement", fontsize=13, fontweight="bold",
                 color=PALETTE["reddit"], pad=12)
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return _save(fig, "reddit_top_posts.png")


# ---------------------------------------------------------------------------
# Chart 5 – Reddit Subreddit Breakdown
# ---------------------------------------------------------------------------
def chart_reddit_subreddits(data: dict) -> Path:
    subs = data.get("top_subreddits", [])[:10]
    if not subs:
        log.warning("No subreddit data.")
        return None

    names = [f"r/{s['subreddit']}" for s in subs]
    counts = [s["post_count"] for s in subs]

    fig, ax = plt.subplots(figsize=(9, 5))
    bar_colours = [PALETTE["reddit"] if i == 0 else "#AA3300" for i in range(len(names))]
    bars = ax.bar(names, counts, color=bar_colours, edgecolor="none")

    for bar, val in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.1,
            str(val),
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.set_ylabel("Post Count")
    ax.set_title("Reddit — Top Subreddits", fontsize=13, fontweight="bold",
                 color=PALETTE["reddit"], pad=12)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.xticks(rotation=35, ha="right", fontsize=8)
    fig.tight_layout()
    return _save(fig, "reddit_subreddits.png")


# ---------------------------------------------------------------------------
# Chart 6 – Cross-Source Unified Trending Scores (Bubble Chart)
# ---------------------------------------------------------------------------
def chart_cross_source(data: dict) -> Path:
    items = data.get("unified_top_trending", [])
    if not items:
        log.warning("No cross-source data.")
        return None

    source_colour = {
        "GitHub": PALETTE["github"],
        "Wikipedia": PALETTE["wikipedia"],
        "Reddit": PALETTE["reddit"],
    }

    fig, ax = plt.subplots(figsize=(12, 6))

    for i, item in enumerate(items):
        colour = source_colour.get(item["source"], PALETTE["accent"])
        size = max(50, item["normalised_score"] * 8)
        ax.scatter(i, item["normalised_score"], s=size, color=colour, alpha=0.85,
                   edgecolors="none", zorder=3)
        label = item["name"][:25] + "…" if len(item["name"]) > 25 else item["name"]
        ax.annotate(
            label,
            xy=(i, item["normalised_score"]),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            fontsize=6.5,
            color=PALETTE["fg"],
        )

    ax.set_xticks([])
    ax.set_ylabel("Normalised Trending Score (0–100)")
    ax.set_title("Cross-Source Unified Trending Scores", fontsize=13,
                 fontweight="bold", color=PALETTE["accent"], pad=12)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    legend_patches = [
        mpatches.Patch(color=c, label=s) for s, c in source_colour.items()
    ]
    ax.legend(handles=legend_patches, loc="upper right", fontsize=9,
              facecolor=PALETTE["bg"], edgecolor=PALETTE["grid"])

    fig.tight_layout()
    return _save(fig, "cross_source_trending.png")


# ---------------------------------------------------------------------------
# HTML Dashboard
# ---------------------------------------------------------------------------
def build_dashboard(chart_paths: list[Path], analysis: dict) -> Path:
    """Embed all PNG charts into a self-contained HTML file."""
    analysed_at = analysis.get("analysed_at", "")
    collected_at = analysis.get("data_collected_at", "")

    def img_tag(path: Path | None) -> str:
        if path is None or not path.exists():
            return "<p style='color:#888'>Chart not available</p>"
        b64 = _fig_to_b64(path)
        return f'<img src="data:image/png;base64,{b64}" style="max-width:100%;border-radius:8px;">'

    sections = [
        ("GitHub Trending", [chart_paths[0], chart_paths[1]]),
        ("Wikipedia Trending", [chart_paths[2]]),
        ("Reddit Trending", [chart_paths[3], chart_paths[4]]),
        ("Cross-Source Overview", [chart_paths[5]]),
    ]

    charts_html = ""
    for title, paths in sections:
        charts_html += f"<h2>{title}</h2><div class='row'>"
        for p in paths:
            charts_html += f"<div class='card'>{img_tag(p)}</div>"
        charts_html += "</div>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TrendPulse Dashboard</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0D1117; color: #C9D1D9; font-family: 'Segoe UI', sans-serif; padding: 24px; }}
  h1 {{ color: #F0A500; font-size: 2rem; margin-bottom: 4px; }}
  .meta {{ color: #8B949E; font-size: 0.85rem; margin-bottom: 24px; }}
  h2 {{ color: #58A6FF; font-size: 1.2rem; margin: 24px 0 12px; border-bottom: 1px solid #21262D; padding-bottom: 6px; }}
  .row {{ display: flex; flex-wrap: wrap; gap: 16px; }}
  .card {{ background: #161B22; border: 1px solid #21262D; border-radius: 10px; padding: 12px; flex: 1 1 400px; }}
  footer {{ margin-top: 40px; color: #555; font-size: 0.75rem; text-align: center; }}
</style>
</head>
<body>
<h1>TrendPulse Dashboard</h1>
<p class="meta">Analysed at: {analysed_at} &nbsp;|&nbsp; Data collected at: {collected_at}</p>
{charts_html}
<footer>Generated by TrendPulse &mdash; Data Pipeline Project</footer>
</body>
</html>"""

    out_path = Path("trendpulse_dashboard.html")
    out_path.write_text(html, encoding="utf-8")
    log.info("Dashboard saved to %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def visualise(input_path: str = INPUT_FILE) -> None:
    """Load analysis results and generate all visualisations."""
    ana_path = Path(input_path)
    if not ana_path.exists():
        raise FileNotFoundError(
            f"'{input_path}' not found. Run task3_analysis.py first."
        )

    log.info("Loading analysis results from %s …", input_path)
    with open(ana_path, "r", encoding="utf-8") as fh:
        analysis = json.load(fh)

    gh = analysis.get("github_analysis", {})
    wiki = analysis.get("wikipedia_analysis", {})
    rd = analysis.get("reddit_analysis", {})
    cross = analysis.get("cross_source", {})

    log.info("Generating charts …")
    paths = [
        chart_github_repos(gh),
        chart_github_languages(gh),
        chart_wikipedia_articles(wiki),
        chart_reddit_posts(rd),
        chart_reddit_subreddits(rd),
        chart_cross_source(cross),
    ]

    saved = [p for p in paths if p is not None]
    log.info("%d chart(s) saved to '%s/'.", len(saved), OUTPUT_DIR)

    dashboard_path = build_dashboard(paths, analysis)

    print("\n=== Visualisation Complete ===")
    print(f"  Charts folder : {OUTPUT_DIR}/")
    for p in saved:
        print(f"    - {p.name}")
    print(f"\n  Dashboard     : {dashboard_path}")
    print("  Open trendpulse_dashboard.html in your browser to view all charts.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    visualise()
