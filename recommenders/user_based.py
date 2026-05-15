"""SVD collaborative filtering for user -> movie recommendations.

Built once at app startup from ratings_clean.csv. Bridges MovieLens movieId
through links.csv to the TMDB id used everywhere else in the app, then runs
truncated SVD with user-mean centering. The dense predicted-ratings matrix
(671 users x ~1959 movies, float32) lives in memory; per-request work is just
a row copy, mask, and top-N argpartition.
"""
from typing import Optional

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

from data_loader import movie_to_list_dict

_state = {
    "predicted": None,    # dense float32 (n_users, n_movies) — user-mean added back
    "seen": None,         # CSR int (n_users, n_movies) — 1 where user rated
    "user_to_idx": None,  # {userId: row idx}
    "tmdb_to_idx": None,  # {tmdbId: col idx}
    "idx_to_tmdb": None,  # row idx -> tmdb id (np.ndarray of int)
    "movies_df": None,    # subset of movies in the SVD universe, indexed by tmdb_id
}

K_FACTORS = 50


def build(ratings_df: pd.DataFrame, links_df: pd.DataFrame, movies_df: pd.DataFrame) -> None:
    """Train SVD and cache the predicted-ratings matrix.

    ratings_df: columns userId, movieId (MovieLens), rating.
    links_df:   columns movieId, tmdbId (used to bridge MovieLens -> TMDB).
    movies_df:  the full app movies DataFrame; only the subset whose id appears
                in the bridged ratings will be served by the recommender.
    """
    # Bridge MovieLens movieId -> tmdbId. Drop rows where the bridge fails or
    # the resulting tmdbId isn't in our movies catalog.
    links = links_df[["movieId", "tmdbId"]].dropna().copy()
    links["movieId"] = links["movieId"].astype(int)
    links["tmdbId"] = links["tmdbId"].astype(int)
    catalog_ids = set(movies_df["id"].astype(int).tolist())

    r = ratings_df[["userId", "movieId", "rating"]].copy()
    r["userId"] = r["userId"].astype(int)
    r["movieId"] = r["movieId"].astype(int)
    r["rating"] = r["rating"].astype(float)

    r = r.merge(links, on="movieId", how="inner")
    r = r[r["tmdbId"].isin(catalog_ids)]
    if r.empty:
        raise RuntimeError("user_recommender: no ratings survived the bridge to TMDB.")

    # Categorical-encode userId and tmdbId.
    user_codes, users = pd.factorize(r["userId"], sort=True)
    movie_codes, tmdb_ids = pd.factorize(r["tmdbId"], sort=True)
    n_users = len(users)
    n_movies = len(tmdb_ids)

    # Per-user mean rating, then center.
    user_means = (
        r.groupby("userId")["rating"].mean().reindex(users).to_numpy(dtype=np.float32)
    )
    centered = r["rating"].to_numpy(dtype=np.float32) - user_means[user_codes]

    # Sparse centered matrix for SVD; sparse 0/1 "seen" mask for serving.
    R_centered = csr_matrix(
        (centered, (user_codes, movie_codes)), shape=(n_users, n_movies)
    )
    seen = csr_matrix(
        (np.ones_like(user_codes, dtype=np.int8), (user_codes, movie_codes)),
        shape=(n_users, n_movies),
    )

    # k must be < min(R.shape); guard for tiny datasets.
    k = min(K_FACTORS, min(R_centered.shape) - 1)
    U, sigma, Vt = svds(R_centered, k=k)
    predicted = (U * sigma).dot(Vt).astype(np.float32)
    predicted += user_means[:, None]
    np.clip(predicted, 0.5, 5.0, out=predicted)

    # Indexed view of movies for fast row lookup at serve time.
    movies_indexed = movies_df.set_index("id", drop=False)

    _state["predicted"] = predicted
    _state["seen"] = seen
    _state["user_to_idx"] = {int(u): i for i, u in enumerate(users)}
    _state["tmdb_to_idx"] = {int(t): i for i, t in enumerate(tmdb_ids)}
    _state["idx_to_tmdb"] = np.asarray(tmdb_ids, dtype=np.int64)
    _state["movies_df"] = movies_indexed

    sparsity = 1.0 - (seen.nnz / float(n_users * n_movies))
    print(
        f"[user_recommender] Built: {n_users} users x {n_movies} movies "
        f"(sparsity {sparsity * 100:.1f}%), k={k}"
    )


def get_status() -> dict:
    if _state["predicted"] is None:
        return {"built": False}
    n_users, n_movies = _state["predicted"].shape
    return {"built": True, "n_users": int(n_users), "n_movies": int(n_movies)}


def has_user(user_id: int) -> bool:
    """Public membership check so callers don't have to peek at _state."""
    mapper = _state["user_to_idx"]
    return mapper is not None and int(user_id) in mapper


def has_movie(movie_id: int) -> bool:
    """Public membership check for TMDB movie ids in the SVD universe."""
    mapper = _state["tmdb_to_idx"]
    return mapper is not None and int(movie_id) in mapper


def predict_rating(user_id: int, movie_id: int) -> Optional[float]:
    """Predicted MovieLens-scale rating (0.5-5.0) for one (user, movie) pair.

    Returns None when either side is outside the trained SVD universe — caller
    decides which 4xx hint to surface via has_user / has_movie.
    """
    if _state["predicted"] is None:
        raise RuntimeError("user_recommender not built. Call build(...) at app startup.")
    u = _state["user_to_idx"].get(int(user_id))
    m = _state["tmdb_to_idx"].get(int(movie_id))
    if u is None or m is None:
        return None
    return round(float(_state["predicted"][u, m]), 2)


def get_user_recommendations(user_id: int, n: int = 10) -> list[dict]:
    if _state["predicted"] is None:
        raise RuntimeError("user_recommender not built. Call build(...) at app startup.")
    idx = _state["user_to_idx"].get(int(user_id))
    if idx is None:
        return []

    scores = _state["predicted"][idx].copy()
    seen_cols = _state["seen"][idx].nonzero()[1]
    scores[seen_cols] = -np.inf

    n = max(1, min(int(n), _state["predicted"].shape[1]))
    top = np.argpartition(-scores, n - 1)[:n]
    top = top[np.argsort(-scores[top])]
    tmdb_ids = _state["idx_to_tmdb"][top]

    out = []
    for tmdb_id in tmdb_ids:
        try:
            row = _state["movies_df"].loc[int(tmdb_id)]
        except KeyError:
            continue
        # If two rows share an id (shouldn't happen post-load, but defensive), take first.
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        out.append(movie_to_list_dict(row))
    return out
