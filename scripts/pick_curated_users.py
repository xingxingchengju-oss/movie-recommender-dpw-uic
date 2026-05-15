"""One-shot analysis to pick 5 curated MovieLens users with distinct genre tastes.

Bridges MovieLens movieId → TMDB id via data/raw/links.csv, then for each user
with at least MIN_RATINGS ratings on movies present in our catalog, computes
their primary_genre distribution. Prints the top candidate per genre so a human
can hand-pick five with sharply differentiated profiles.

Usage:
    python scripts/pick_curated_users.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402

MIN_RATINGS = 50
TOP_PER_GENRE = 3


def main():
    ratings = pd.read_csv(config.RATINGS_CSV, usecols=["userId", "movieId", "rating"])
    links = pd.read_csv(
        config.LINKS_CSV,
        usecols=["movieId", "tmdbId"],
        dtype={"movieId": "Int64", "tmdbId": "Int64"},
    ).dropna(subset=["tmdbId"])
    movies = pd.read_csv(
        config.MOVIES_CSV,
        usecols=["id", "title", "genres_parsed"],
        encoding="utf-8",
        encoding_errors="replace",
    )
    movies["genres_list"] = movies["genres_parsed"].fillna("").apply(
        lambda v: [g for g in str(v).split("|") if g]
    )
    movies = movies.dropna(subset=["id"])
    movies["id"] = pd.to_numeric(movies["id"], errors="coerce").astype("Int64")
    movies = movies.dropna(subset=["id"])

    # Bridge: ratings.movieId (MovieLens) -> tmdbId via links.csv -> movies.id
    bridged = ratings.merge(links, on="movieId", how="inner")
    bridged = bridged.merge(
        movies, left_on="tmdbId", right_on="id", how="inner"
    )
    print(
        f"[picker] Bridged: {len(bridged):,} ratings · "
        f"{bridged['userId'].nunique()} users · "
        f"{bridged['tmdbId'].nunique()} linked movies"
    )

    counts = bridged.groupby("userId").size()
    qualifying = counts[counts >= MIN_RATINGS].index
    print(f"[picker] {len(qualifying)} users have >= {MIN_RATINGS} linked ratings")

    bridged = bridged[bridged["userId"].isin(qualifying)].copy()

    # Multi-label genre attribution: each rating contributes to ALL its movie's
    # genres. This surfaces taste signals (Sci-fi, Animation, Horror) that the
    # single-label primary_genre buries under the dominant Drama/Comedy buckets.
    per_user_total = bridged.groupby("userId").size()
    exploded = bridged.explode("genres_list").rename(columns={"genres_list": "genre"})
    exploded = exploded[exploded["genre"].notna() & (exploded["genre"] != "")]

    genre_counts = exploded.groupby(["userId", "genre"]).size().reset_index(name="n")
    genre_counts["share"] = genre_counts.apply(
        lambda r: r["n"] / per_user_total[r["userId"]], axis=1
    )
    genre_counts = genre_counts.merge(
        per_user_total.rename("total"), left_on="userId", right_index=True
    )
    genre_counts = genre_counts.rename(columns={"genre": "primary_genre"})

    # For each user, keep only their top genre.
    top_per_user = (
        genre_counts.sort_values(["userId", "share"], ascending=[True, False])
        .groupby("userId")
        .head(1)
        .reset_index(drop=True)
    )

    # Print the top TOP_PER_GENRE candidates for each genre, sorted by share desc.
    print("\n[picker] Top candidates per genre (share, n_genre / n_total):\n")
    for genre, group in top_per_user.sort_values("primary_genre").groupby("primary_genre"):
        group = group.sort_values("share", ascending=False).head(TOP_PER_GENRE)
        print(f"  {genre}  (best share: {group['share'].iloc[0]:.2f})")
        for _, row in group.iterrows():
            print(
                f"    userId={int(row['userId']):>4}  "
                f"share={row['share']:.2f}  "
                f"n={int(row['n']):>3} / {int(row['total']):>3}"
            )

    print(
        "\n[picker] Pick 5 with distinct top genres and edit curated_users.py manually."
    )


if __name__ == "__main__":
    main()
