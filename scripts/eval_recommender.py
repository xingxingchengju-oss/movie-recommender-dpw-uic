"""Offline evaluation of the SVD user recommender.

80/20 random split on ratings (after MovieLens->TMDB bridging). Trains SVD on
the 80% via user_recommender.build(), then computes:
  - RMSE on the held-out 20% (only pairs where both user and movie were seen
    in train; the rest are unservable for SVD)
  - Precision@10: for each user with >= MIN_TEST_LIKES liked test ratings
    (rating >= LIKED_THRESHOLD), what fraction of the top-10 recommendations
    are in their liked test set

Usage:
    python scripts/eval_recommender.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from recommenders import user_based as user_recommender  # noqa: E402
from data_loader import load_movies  # noqa: E402

RANDOM_STATE = 42
TEST_FRAC = 0.20
LIKED_THRESHOLD = 4.0
MIN_TEST_LIKES = 5
TOP_K = 10


def main():
    print("[eval] Loading data...")
    movies, _ = load_movies()
    ratings = pd.read_csv(config.RATINGS_CSV)
    links = pd.read_csv(config.LINKS_CSV)

    # Bridge before splitting so the train/test sets only contain SVD-servable pairs.
    links_min = links[["movieId", "tmdbId"]].dropna().astype({"movieId": int, "tmdbId": int})
    catalog_ids = set(movies["id"].astype(int).tolist())
    bridged = ratings.merge(links_min, on="movieId", how="inner")
    bridged = bridged[bridged["tmdbId"].isin(catalog_ids)].reset_index(drop=True)
    print(f"[eval] Bridged ratings: {len(bridged):,}")

    rng = np.random.default_rng(RANDOM_STATE)
    is_test = rng.random(len(bridged)) < TEST_FRAC
    train = bridged[~is_test].copy()
    test = bridged[is_test].copy()
    print(f"[eval] Train: {len(train):,}  Test: {len(test):,}")

    # Build SVD on the train slice. Pass it through the public API so we test
    # exactly the production code path.
    user_recommender.build(train, links_min, movies)

    user_to_idx = user_recommender._state["user_to_idx"]
    idx_to_tmdb = user_recommender._state["idx_to_tmdb"]
    predicted = user_recommender._state["predicted"]
    tmdb_to_idx = {int(t): i for i, t in enumerate(idx_to_tmdb)}

    # RMSE on the held-out test pairs that are servable (both user and tmdbId
    # were seen during training).
    test["user_idx"] = test["userId"].map(user_to_idx)
    test["movie_idx"] = test["tmdbId"].map(tmdb_to_idx)
    servable = test.dropna(subset=["user_idx", "movie_idx"]).copy()
    servable["user_idx"] = servable["user_idx"].astype(int)
    servable["movie_idx"] = servable["movie_idx"].astype(int)
    print(
        f"[eval] Test pairs servable by SVD: {len(servable):,} "
        f"({len(servable) / len(test) * 100:.1f}%)"
    )

    y_pred = predicted[servable["user_idx"].to_numpy(), servable["movie_idx"].to_numpy()]
    y_true = servable["rating"].to_numpy(dtype=np.float32)
    rmse = float(np.sqrt(np.mean((y_pred - y_true) ** 2)))
    mae = float(np.mean(np.abs(y_pred - y_true)))
    print(f"[eval] RMSE = {rmse:.4f}   MAE = {mae:.4f}")

    # Precision@K: per user, recommend top-K via the production helper, count
    # how many fall into their liked test set.
    liked_test = servable[servable["rating"] >= LIKED_THRESHOLD]
    per_user_likes = liked_test.groupby("userId")["tmdbId"].apply(set)
    eligible_users = [uid for uid, s in per_user_likes.items() if len(s) >= MIN_TEST_LIKES]
    print(
        f"[eval] Users with >= {MIN_TEST_LIKES} liked test ratings: "
        f"{len(eligible_users)}"
    )

    precisions = []
    for uid in eligible_users:
        recs = user_recommender.get_user_recommendations(int(uid), n=TOP_K)
        if not recs:
            continue
        rec_ids = {int(r["id"]) for r in recs}
        hits = len(rec_ids & per_user_likes[uid])
        precisions.append(hits / TOP_K)

    p_at_k = float(np.mean(precisions)) if precisions else 0.0
    print(f"[eval] Precision@{TOP_K} = {p_at_k:.4f} (averaged over {len(precisions)} users)")
    print()
    print(f"SUMMARY: RMSE={rmse:.4f}  MAE={mae:.4f}  P@{TOP_K}={p_at_k:.4f}")


if __name__ == "__main__":
    main()
