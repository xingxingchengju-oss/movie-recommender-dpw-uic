import os

import pandas as pd

import config

CANONICAL_GENRES = {
    "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
    "Drama", "Family", "Fantasy", "Foreign", "History", "Horror", "Music",
    "Mystery", "Romance", "Science Fiction", "TV Movie", "Thriller", "War",
    "Western",
}


def _split_pipe(value):
    if pd.isna(value) or value == "":
        return []
    return [s for s in str(value).split("|") if s]


def _build_poster_lookup(tmdb_ids):
    """Map tmdb_id -> /static/posters/tt*.jpg URL or None when no poster file exists.

    Uses the actual filesystem (static/posters/) as the existence check, not
    data/processed/imdb_id.csv — that file is incomplete (lists 7,533 of the
    8,473 actual posters), so trusting it would silently drop ~676 valid matches.
    """
    links = pd.read_csv(
        config.LINKS_CSV,
        dtype={"imdbId": str, "tmdbId": str, "movieId": str},
        usecols=["imdbId", "tmdbId"],
    )
    available = {f for f in os.listdir(config.POSTERS_DIR) if f.endswith(".jpg")}

    lookup = {tid: None for tid in tmdb_ids}
    for _, row in links.dropna(subset=["imdbId", "tmdbId"]).iterrows():
        tmdb_id = row["tmdbId"]
        fname = f"tt{row['imdbId'].zfill(7)}.jpg"
        if tmdb_id in lookup and fname in available:
            lookup[tmdb_id] = f"{config.POSTER_URL_PREFIX}/{fname}"
    return lookup


def load_movies():
    df = pd.read_csv(config.MOVIES_CSV, encoding="utf-8", encoding_errors="replace")
    df = df.dropna(axis=1, how="all")
    df = df.dropna(subset=["id", "title"])
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df = df.dropna(subset=["id"])
    df["id"] = df["id"].astype(int)
    for col in ("release_year", "vote_count"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Derive release_decade from release_year — the CSV column has corrupt values
    # (e.g. 4, 6, 1959, 1976) from the same column-shift issue. Recomputing from
    # the cleaned release_year guarantees decade values are always multiples of 10.
    df["release_decade"] = (df["release_year"] // 10 * 10).astype("Float64")
    for col in ("vote_average", "runtime", "budget", "revenue", "profit", "roi", "popularity"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Sanity filter: drop rows where CSV column-shift corruption put implausible
    # values into vote_average / release_year / title. These are the same class
    # of breakage as the 7 NaN-title rows already dropped; here we catch shifts
    # that left a non-NaN but out-of-range value in place.
    before = len(df)
    title_str = df["title"].astype(str)
    rating_ok = df["vote_average"].isna() | df["vote_average"].between(0, 10, inclusive="both")
    year_ok = df["release_year"].isna() | df["release_year"].between(1874, 2017, inclusive="both")
    title_ok = ~title_str.str.contains("�", regex=False) & ~title_str.str.match(r"^[\d./\s]+$")
    df = df[rating_ok & year_ok & title_ok].copy()
    print(f"[data_loader] Sanity filter dropped {before - len(df)} additional column-shifted rows.")

    df["genres_list"] = df["genres_parsed"].apply(
        lambda v: [g for g in _split_pipe(v) if g in CANONICAL_GENRES]
    )
    df["keywords_list"] = df["keywords_parsed"].apply(_split_pipe)
    df["top_cast_list"] = df.get("top_cast", pd.Series([""] * len(df))).apply(_split_pipe)
    df.loc[~df["primary_genre"].isin(CANONICAL_GENRES), "primary_genre"] = None

    poster_lookup = _build_poster_lookup(df["id"].astype(str).tolist())
    df["poster_url"] = df["id"].astype(str).map(poster_lookup)

    # IMDb-style Bayesian-weighted score for the "Popular" sort. Movies with
    # few votes get pulled toward the global mean; only films that are both
    # well-rated AND widely-voted float to the top. Computed once at startup.
    rated = df[df["vote_count"] > 0]
    C = float(rated["vote_average"].mean())
    m = float(rated["vote_count"].quantile(0.90))
    v = df["vote_count"].fillna(0)
    R = df["vote_average"].fillna(C)
    df["weighted_score"] = (v / (v + m)) * R + (m / (v + m)) * C
    print(f"[data_loader] Popular ranking: C={C:.2f}, m={m:.0f} (90th-pct vote_count)")

    genres_set = sorted(CANONICAL_GENRES)
    return df, genres_set


def movie_to_list_dict(row):
    """Slim payload for list view."""
    return {
        "id": int(row["id"]),
        "title": row["title"],
        "release_year": int(row["release_year"]) if pd.notna(row["release_year"]) else None,
        "primary_genre": row["primary_genre"] if pd.notna(row.get("primary_genre")) else None,
        "vote_average": float(row["vote_average"]) if pd.notna(row["vote_average"]) else None,
        "poster_url": row["poster_url"] if pd.notna(row["poster_url"]) else None,
    }


def movie_to_detail_dict(row):
    """Full payload for detail view."""
    def _num(v):
        return float(v) if pd.notna(v) else None

    def _int(v):
        return int(v) if pd.notna(v) else None

    return {
        "id": int(row["id"]),
        "title": row["title"],
        "release_year": _int(row["release_year"]),
        "release_decade": _int(row["release_decade"]),
        "primary_genre": row["primary_genre"] if pd.notna(row.get("primary_genre")) else None,
        "genres": row["genres_list"],
        "keywords": row["keywords_list"],
        "overview": row["overview"] if pd.notna(row.get("overview")) else "",
        "vote_average": _num(row["vote_average"]),
        "vote_count": _int(row.get("vote_count")),
        "director": row["director"] if pd.notna(row.get("director")) else None,
        "top_cast": row["top_cast_list"],
        "runtime": _num(row.get("runtime")),
        "budget": _num(row.get("budget")),
        "revenue": _num(row.get("revenue")),
        "profit": _num(row.get("profit")),
        "roi": _num(row.get("roi")),
        "popularity": _num(row.get("popularity")),
        "original_language": row.get("original_language") if pd.notna(row.get("original_language")) else None,
        "countries": row.get("countries") if pd.notna(row.get("countries")) else None,
        "poster_url": row["poster_url"] if pd.notna(row["poster_url"]) else None,
    }
