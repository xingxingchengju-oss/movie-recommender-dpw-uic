"""SVD collaborative filtering for user -> movie recommendations.

Built once at app startup from ratings_clean.csv. Bridges MovieLens movieId
through links.csv to the TMDB id used everywhere else in the app, then runs
truncated SVD with user-mean centering. The dense predicted-ratings matrix
(671 users x ~1959 movies, float32) lives in memory; per-request work is just
a row copy, mask, and top-N argpartition.
"""
from typing import List, Optional

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

from data_loader import CANONICAL_GENRES, movie_to_list_dict

_state = {
    "predicted": None,       # dense float32 (n_users, n_movies) — user-mean added back
    "seen": None,            # CSR int (n_users, n_movies) — 1 where user rated
    "user_to_idx": None,     # {userId: row idx}
    "tmdb_to_idx": None,     # {tmdbId: col idx}
    "idx_to_tmdb": None,     # row idx -> tmdb id (np.ndarray of int)
    "movies_df": None,       # subset of movies in the SVD universe, indexed by tmdb_id
    # V2B3 fold-in factors:
    "Vt": None,              # (k, n_movies) f32 — singular vectors for the item axis
    "sigma": None,           # (k,) f32 — singular values, paired with Vt as svds returned them
    "global_mean": None,     # f32 — synthetic-user baseline (mean of all bridged ratings)
    "allowed_genres": None,  # set[str] — canonical genre filter for Build Your Own
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

    # Global mean across all bridged ratings — used as the synthetic-user
    # baseline in fold-in (a new "I like these films" user can't be centered
    # against its own all-5.0 inputs; that would collapse the centered vector).
    global_mean = float(r["rating"].mean())

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
    # V2B3 fold-in factors. Vt is small (k x n_movies ~ 50 x 1956 = 400 KB f32).
    _state["Vt"] = Vt.astype(np.float32)
    _state["sigma"] = sigma.astype(np.float32)
    _state["global_mean"] = np.float32(global_mean)
    _state["allowed_genres"] = set(CANONICAL_GENRES)

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


def _serialize_top_indices(top_indices: np.ndarray) -> list:
    """Map a column-index array to a list of movie_to_list_dict payloads."""
    tmdb_ids = _state["idx_to_tmdb"][top_indices]
    out = []
    for tmdb_id in tmdb_ids:
        try:
            row = _state["movies_df"].loc[int(tmdb_id)]
        except KeyError:
            continue
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        out.append(movie_to_list_dict(row))
    return out


def fold_in_scores(liked_movie_ids: List[int]):
    """Run the fold-in projection and return raw predicted-rating scores.

    Used by recommenders.hybrid (V2C) and by recommend_from_synthetic_user
    below. Returns:

        scores:      np.ndarray (n_movies,) f32, predicted rating ∈ [0.5, 5.0]
                     for every movie in the SVD universe. Liked movies are NOT
                     yet masked — the caller decides.
        used_cols:   np.ndarray (k_used,) int64, column indices in the SVD
                     universe of liked movies that were found.
        used_ids:    list[int] of tmdb ids actually projected
        ignored_ids: list[int] of tmdb ids dropped because they're not in
                     the SVD universe

    Returns (None, ..., used_ids=[], ignored_ids=all-deduped) when no liked
    id is in the SVD set — callers above the boundary should handle that.
    """
    if _state["predicted"] is None:
        raise RuntimeError("user_recommender not built. Call build(...) at app startup.")

    tmdb_to_idx = _state["tmdb_to_idx"]
    seen_for_dedup = set()
    used_ids: List[int] = []
    ignored_ids: List[int] = []
    for raw in liked_movie_ids:
        try:
            mid = int(raw)
        except (TypeError, ValueError):
            continue
        if mid in seen_for_dedup:
            continue
        seen_for_dedup.add(mid)
        if mid in tmdb_to_idx:
            used_ids.append(mid)
        else:
            ignored_ids.append(mid)

    if not used_ids:
        return None, np.empty(0, dtype=np.int64), used_ids, ignored_ids

    Vt = _state["Vt"]
    sigma = _state["sigma"]
    mu = float(_state["global_mean"])
    n_movies = Vt.shape[1]

    r_centered = np.zeros(n_movies, dtype=np.float32)
    used_cols = np.fromiter(
        (tmdb_to_idx[m] for m in used_ids), dtype=np.int64, count=len(used_ids)
    )
    r_centered[used_cols] = np.float32(5.0 - mu)

    sigma_safe = np.maximum(sigma, np.float32(1e-6))
    u_new = (r_centered @ Vt.T) / sigma_safe
    scores = (u_new * sigma) @ Vt + mu
    scores = scores.astype(np.float32, copy=False)

    return scores, used_cols, used_ids, ignored_ids


def recommend_from_synthetic_user(
    liked_movie_ids: List[int],
    n: int = 20,
    genre: Optional[str] = None,
) -> dict:
    """SVD fold-in for an ad-hoc 'I like these films' user.

    Steps:
      1. Validate + dedupe liked_movie_ids against the SVD universe.
      2. Build a centered rating vector r_centered around the training global
         mean (NOT the synthetic user's own mean — that collapses to zero).
      3. Project: u_new = r_centered @ V / sigma_safe        # in latent space
      4. Reconstruct: scores = u_new * sigma @ Vt + mu       # back to ratings
      5. Mask liked movies + optional primary_genre filter.
      6. Bail out if no finite candidates remain (e.g. genre filter wiped all).
      7. Top-N argpartition.

    Note on sigma: mathematically the division in step 3 and the multiplication
    in step 4 cancel, so step 4 is equivalent to r_centered @ V @ Vt + mu. We
    keep both factors visible because the two-step form documents the algorithm
    cleanly and lets us guard with sigma_safe = max(sigma, 1e-6) against tiny
    singular values without changing the math.
    """
    # ---- Steps 1-4 are shared with hybrid via fold_in_scores ----
    scores, used_cols, used_ids, ignored_ids = fold_in_scores(liked_movie_ids)
    if scores is None:
        raise ValueError(
            "none of the selected movies are in the SVD index — try titles like "
            "The Godfather, Shawshank Redemption, Toy Story, or Pulp Fiction "
            "(popular newer releases such as Inception fall outside the "
            "MovieLens snapshot)"
        )
    n_movies = scores.shape[0]

    # ---- Step 5: mask liked movies + optional genre filter ----
    scores = scores.copy()  # don't mutate the cached factors via the returned view
    scores[used_cols] = -np.inf

    allowed_genres = _state["allowed_genres"] or set()
    genre_norm = (genre or "").strip()
    apply_genre = bool(genre_norm) and genre_norm in allowed_genres
    if apply_genre:
        movies_df = _state["movies_df"]
        idx_to_tmdb = _state["idx_to_tmdb"]
        # Build a boolean mask of "column matches genre" once.
        match_mask = np.zeros(n_movies, dtype=bool)
        for col, tmdb_id in enumerate(idx_to_tmdb):
            try:
                pg = movies_df.loc[int(tmdb_id), "primary_genre"]
            except KeyError:
                continue
            if isinstance(pg, pd.Series):
                pg = pg.iloc[0]
            if pg == genre_norm:
                match_mask[col] = True
        scores[~match_mask] = -np.inf

    # ---- Step 6: bail out if nothing finite remains ----
    finite_mask = np.isfinite(scores)
    finite_count = int(finite_mask.sum())
    if finite_count == 0:
        hint = (
            "No candidates left after the genre filter — try 'Any' or pick a "
            "different genre."
            if apply_genre
            else "No fold-in candidates available for these picks."
        )
        return {
            "recommendations": [],
            "used_ids": used_ids,
            "ignored_ids": ignored_ids,
            "hint": hint,
        }

    # ---- Step 7: top-N ----
    n = max(1, min(int(n), finite_count))
    # argpartition needs the partition index < len; finite_count >= n is guaranteed above.
    top = np.argpartition(-scores, n - 1)[:n]
    top = top[np.argsort(-scores[top])]

    return {
        "recommendations": _serialize_top_indices(top),
        "used_ids": used_ids,
        "ignored_ids": ignored_ids,
    }
