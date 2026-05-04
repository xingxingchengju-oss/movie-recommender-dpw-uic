"""Reelvana Q1/Q2 analysis functions.

Each function takes a DataFrame and returns a plain Python dict of raw data.
No Plotly/matplotlib config — visualization is the caller's job. This lets
the same logic feed both the web dashboard (Plotly.js) and the notebook
(matplotlib), guaranteeing the numbers stay in sync.
"""

import numpy as np
import pandas as pd


def _financial_subset(df):
    """Rows where budget AND revenue are both disclosed (positive, non-null)."""
    return df[(df["budget"] > 0) & (df["revenue"] > 0)]


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


def genre_evolution_by_decade(df, top_n=8):
    """Counts of top-N genres across decades. Q1.2 — stacked area chart.

    Returns matrix shape (n_decades, n_genres) so each column is one genre's
    series across time.
    """
    genres = _top_n_genres(df, top_n)
    sub = df[df["primary_genre"].isin(genres) & df["release_decade"].notna()]
    pivot = (
        sub.groupby(["release_decade", "primary_genre"]).size().unstack(fill_value=0)
    )
    pivot = pivot.reindex(columns=genres, fill_value=0).sort_index()
    return {
        "decades": [int(d) for d in pivot.index.tolist()],
        "genres": genres,
        "matrix": pivot.values.tolist(),
    }


def genre_decade_heatmap(df, top_n=8):
    """Same data as genre_evolution but row-normalized — Q1.3 heatmap.

    Each decade row sums to 1.0, so cells show that decade's genre share.
    """
    raw = genre_evolution_by_decade(df, top_n=top_n)
    matrix = np.asarray(raw["matrix"], dtype=float)
    row_sums = matrix.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0  # avoid div-by-zero on empty decades
    normalized = matrix / row_sums
    return {
        "decades": raw["decades"],
        "genres": raw["genres"],
        "matrix": normalized.tolist(),
    }


# ────────────────────────────── Q2: Financials ──────────────────────────

def budget_revenue_scatter(df, max_points=4000):
    """Scatter + linear regression. Q2.1.

    Subsamples to max_points for browser rendering performance (random seed
    fixed so the chart is stable across reloads).
    """
    sub = _financial_subset(df)
    n_total = len(sub)
    if n_total > max_points:
        sub = sub.sample(n=max_points, random_state=42)

    budget = sub["budget"].values
    revenue = sub["revenue"].values
    slope, intercept = np.polyfit(budget, revenue, 1)

    return {
        "budget": budget.tolist(),
        "revenue": revenue.tolist(),
        "regression": {
            "slope": float(slope),
            "intercept": float(intercept),
        },
        "n_movies": int(n_total),
        "n_plotted": int(len(sub)),
    }


def roi_by_genre_box(df, top_n=8, roi_cap=50):
    """ROI distribution per top genre. Q2.2 — box plot.

    Filters out extreme outliers (roi > roi_cap) so the box plot is readable.
    """
    fin = _financial_subset(df)
    fin = fin[fin["roi"].notna() & (fin["roi"] < roi_cap)]
    genres = _top_n_genres(fin, top_n)
    fin = fin[fin["primary_genre"].isin(genres)]

    roi_by_genre = {
        g: fin[fin["primary_genre"] == g]["roi"].tolist() for g in genres
    }
    return {
        "genres": genres,
        "roi_by_genre": roi_by_genre,
        "n_movies": int(len(fin)),
        "roi_cap": roi_cap,
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
}
