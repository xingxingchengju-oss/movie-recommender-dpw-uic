"""Reelvana Q1/Q2 analysis functions.

Each function takes a DataFrame and returns a plain Python dict of raw data.
No Plotly/matplotlib config — visualization is the caller's job. This lets
the same logic feed both the web dashboard (Plotly.js) and the notebook
(matplotlib), guaranteeing the numbers stay in sync.
"""

import numpy as np
import pandas as pd


def _financial_subset(df, min_budget=1000):
    """Rows where budget AND revenue are both disclosed and plausible.

    `min_budget=1000` filters out data-entry artifacts where budget is recorded
    as $1, $10, $100 (not real production budgets). 36 rows are filtered.
    """
    return df[(df["budget"] >= min_budget) & (df["revenue"] > 0)]


def _top_n_genres(df, n):
    """Top N primary_genre values by frequency, derived dynamically from df."""
    return df["primary_genre"].dropna().value_counts().head(n).index.tolist()


# ────────────────────────────── Q1: Trends ──────────────────────────────

def production_trend_by_decade(df):
    """Movie count per release decade. Q1.1 — line/bar chart."""
    s = df["release_decade"].dropna().astype(int).value_counts().sort_index()
    return {
        "decades": s.index.tolist(),
        "counts": s.values.tolist(),
    }


def genre_evolution_by_decade(df, top_n=8, min_films_per_decade=50):
    """Per-decade share of top-N genres. Q1.2 — percentage-stacked area.

    Filters decades with fewer than `min_films_per_decade` films to avoid
    misleading 100% blocks from tiny early-cinema samples (1870s/1880s have
    just 1-3 films each — a single Documentary classification produces a
    visually dominant 100% block at the chart's left edge).

    Returns share matrix (each row sums to 1.0) so the chart shows composition
    evolution rather than just volume growth (which Production Trend covers).
    `counts_matrix` retained alongside for raw-count callers.
    """
    genres = _top_n_genres(df, top_n)
    sub = df[df["primary_genre"].isin(genres) & df["release_decade"].notna()]
    pivot = (
        sub.groupby(["release_decade", "primary_genre"]).size().unstack(fill_value=0)
    )
    pivot = pivot.reindex(columns=genres, fill_value=0).sort_index()
    pivot = pivot[pivot.sum(axis=1) >= min_films_per_decade]
    counts = pivot.values
    row_sums = counts.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    shares = counts / row_sums
    return {
        "decades": [int(d) for d in pivot.index.tolist()],
        "genres": genres,
        "matrix": shares.tolist(),          # percentages (rows sum to 1.0)
        "counts_matrix": counts.tolist(),   # raw counts (for notebook / drill-down)
        "min_films_per_decade": min_films_per_decade,
    }


def genre_decade_heatmap(df, top_n=8):
    """Q1.3 heatmap — row-normalized genre share per decade.

    Same data as `genre_evolution_by_decade()['matrix']` (already share),
    plus per-decade sample size so the chart can flag small-sample decades
    (e.g. 1870s/1880s have just 1-3 films, where 100% Documentary is noise).
    """
    raw = genre_evolution_by_decade(df, top_n=top_n)
    counts = np.asarray(raw["counts_matrix"], dtype=int)
    sample_per_decade = counts.sum(axis=1).tolist()
    return {
        "decades": raw["decades"],
        "genres": raw["genres"],
        "matrix": raw["matrix"],  # already normalized
        "sample_per_decade": [int(s) for s in sample_per_decade],
    }


# ────────────────────────────── Q2: Financials ──────────────────────────

def budget_revenue_scatter(df, max_points=4000):
    """Scatter + log-log regression. Q2.1.

    Regression is computed in log10-log10 space (the chart is rendered on log
    axes), so the line plots as a true diagonal. The slope is a price
    elasticity: a 1% increase in budget yields ~`slope`% increase in revenue.
    Median(revenue/budget) is returned separately for the "$X per $1" insight —
    it's the honest central tendency for a heavily right-skewed ratio.
    """
    sub_full = _financial_subset(df)
    n_total = len(sub_full)
    median_ratio = float((sub_full["revenue"] / sub_full["budget"]).median())

    sub = sub_full
    if n_total > max_points:
        sub = sub_full.sample(n=max_points, random_state=42)

    budget = sub["budget"].values
    revenue = sub["revenue"].values

    # Log-log regression on the full disclosed set (not the subsample)
    log_b = np.log10(sub_full["budget"].values)
    log_r = np.log10(sub_full["revenue"].values)
    slope, intercept = np.polyfit(log_b, log_r, 1)
    x_min, x_max = float(log_b.min()), float(log_b.max())
    line_x = [10 ** x_min, 10 ** x_max]
    line_y = [10 ** (slope * x_min + intercept), 10 ** (slope * x_max + intercept)]

    return {
        "budget": budget.tolist(),
        "revenue": revenue.tolist(),
        "regression": {
            "slope": float(slope),
            "intercept": float(intercept),
            "x": line_x,
            "y": line_y,
        },
        "median_ratio": round(median_ratio, 2),
        "n_movies": int(n_total),
        "n_plotted": int(len(sub)),
    }


def roi_by_genre_box(df, top_n=8, roi_cap=50, roi_min=1.0):
    """ROI distribution per top genre. Q2.2 — box plot.

    Filters:
    - `roi >= roi_min` (default 1.0 = at least broke even). Films with
      ROI < 1 lost money; including them drags the log Y-axis down to
      micro/nano values that pollute the chart and aren't actionable.
    - `roi < roi_cap` (default 50×) caps mega-outliers like Blair Witch.

    Genres sorted by median ROI desc; per-genre summary stats returned
    for clean tooltips (avoids Plotly's 6-stat default box hover).
    """
    fin = _financial_subset(df)
    fin = fin[fin["roi"].notna() & (fin["roi"] >= roi_min) & (fin["roi"] < roi_cap)]
    candidates = _top_n_genres(fin, top_n)
    fin = fin[fin["primary_genre"].isin(candidates)]

    medians = {g: float(fin[fin["primary_genre"] == g]["roi"].median()) for g in candidates}
    genres = sorted(candidates, key=lambda g: -medians[g])
    summary = {}
    roi_by_genre = {}
    for g in genres:
        s = fin[fin["primary_genre"] == g]["roi"]
        roi_by_genre[g] = s.tolist()
        summary[g] = {
            "median": round(float(s.median()), 2),
            "q1":     round(float(s.quantile(0.25)), 2),
            "q3":     round(float(s.quantile(0.75)), 2),
            "n":      int(len(s)),
        }
    return {
        "genres": genres,
        "roi_by_genre": roi_by_genre,
        "summary": summary,
        "n_movies": int(len(fin)),
        "roi_min": roi_min,
        "roi_cap": roi_cap,
    }


# ────────────────────────────── Q3: Audience ────────────────────────────

def rating_distribution(df, bin_width=0.5):
    """Histogram of vote_average. Q3.1 — distribution of audience ratings."""
    rated = df["vote_average"].dropna()
    bins = np.arange(0, 10 + bin_width, bin_width)
    counts, _ = np.histogram(rated, bins=bins)
    return {
        "bin_edges": bins.tolist(),
        "counts": counts.tolist(),
        "n_movies": int(len(rated)),
        "median": float(rated.median()),
        "mean": float(rated.mean()),
    }


def rating_trend(df, min_votes=10, min_films_per_decade=20):
    """Average rating per decade. Q3.2 — how audience tastes shifted over time.

    Two filters:
    - `min_votes`: drop films with too few ratings (noise per film)
    - `min_films_per_decade`: drop decades with too few films (noise per decade)
      — 1880s with n=3 produces a 4.8 trough that's pure sampling noise.
    """
    sub = df[(df["vote_count"] >= min_votes) & df["release_decade"].notna()]
    grouped = sub.groupby("release_decade")
    avg = grouped["vote_average"].mean()
    n = grouped.size()
    keep = n >= min_films_per_decade
    avg = avg[keep]
    n = n[keep]
    return {
        "decades": [int(d) for d in avg.index.tolist()],
        "avg_rating": [round(v, 3) for v in avg.values.tolist()],
        "n_movies": [int(c) for c in n.values.tolist()],
        "min_votes_filter": min_votes,
        "min_films_per_decade": min_films_per_decade,
    }


def rating_by_genre(df, top_n=8, min_votes=10):
    """Rating distribution per top genre. Q3.3 — which genres audiences love.

    Genres sorted by median rating descending, so the chart reads
    high-to-low left-to-right (matches the "rating hierarchy" insight).
    """
    sub = df[(df["vote_count"] >= min_votes) & df["primary_genre"].notna()]
    candidates = _top_n_genres(sub, top_n)
    sub = sub[sub["primary_genre"].isin(candidates)]
    medians = {g: float(sub[sub["primary_genre"] == g]["vote_average"].median()) for g in candidates}
    genres = sorted(candidates, key=lambda g: -medians[g])
    summary = {}
    rating_by_genre = {}
    for g in genres:
        s = sub[sub["primary_genre"] == g]["vote_average"]
        rating_by_genre[g] = s.tolist()
        summary[g] = {
            "median": round(float(s.median()), 2),
            "q1":     round(float(s.quantile(0.25)), 2),
            "q3":     round(float(s.quantile(0.75)), 2),
            "n":      int(len(s)),
        }
    return {
        "genres": genres,
        "rating_by_genre": rating_by_genre,
        "summary": summary,
        "medians": {g: round(medians[g], 2) for g in genres},
        "n_movies": int(len(sub)),
        "min_votes_filter": min_votes,
    }


def financial_correlation(df):
    """Pearson correlation matrix on financial + runtime metrics. Q2.3."""
    fin = _financial_subset(df)
    cols = ["budget", "revenue", "profit", "roi", "runtime"]
    available = [c for c in cols if c in fin.columns]
    matrix = fin[available].corr().values
    return {
        "variables": [c.capitalize() for c in available],
        "matrix": matrix.tolist(),
        "n_movies": int(len(fin.dropna(subset=available))),
    }


# ────────────────────────────── KPIs ────────────────────────────────────

def kpi_summary(df):
    """Top-of-dashboard KPI cards.

    All counts are derived from `df` at runtime — never hardcoded.
    'Total Revenue' was rejected (cross-century sum without inflation
    adjustment is misleading); replaced with 'Average ROI (disclosed)'.
    """
    total_movies = len(df)

    rated = df["vote_average"].dropna()
    avg_rating = float(rated.mean()) if len(rated) else 0.0

    genre_counts = df["primary_genre"].dropna().value_counts()
    if len(genre_counts):
        top_name = str(genre_counts.index[0])
        top_count = int(genre_counts.iloc[0])
    else:
        top_name, top_count = "—", 0

    fin = _financial_subset(df)
    n_disclosed = int(len(fin))
    # Use median: ROI is highly right-skewed (micro-budget hits like Blair Witch
    # produce massive outliers that distort the mean to ~29000x).
    median_roi = float(fin["roi"].median()) if n_disclosed else 0.0

    return {
        "total_movies": total_movies,
        "avg_rating": round(avg_rating, 2),
        "top_genre": {"name": top_name, "count": top_count},
        "median_roi_disclosed": round(median_roi, 2),
        "disclosed_count": n_disclosed,
    }


# ────────────────────────────── Registry ────────────────────────────────

CHART_FUNCTIONS = {
    "production_trend": production_trend_by_decade,
    "genre_evolution": genre_evolution_by_decade,
    "genre_heatmap": genre_decade_heatmap,
    "budget_revenue": budget_revenue_scatter,
    "roi_by_genre": roi_by_genre_box,
    "financial_correlation": financial_correlation,
    "rating_distribution": rating_distribution,
    "rating_trend": rating_trend,
    "rating_by_genre": rating_by_genre,
}
