"""Hybrid recommender combining V1 TF-IDF item-item and V2A SVD fold-in.

V2C entry point. Given a list of liked TMDB ids, computes two parallel score
vectors (one from V1's TF-IDF cosine similarity aggregated over the seeds,
one from V2A's SVD fold-in), min-max normalizes both to [0, 1], then linearly
blends:

    final_score[m] = (1 - alpha) * content_norm[m] + alpha * cf_norm[m]

alpha=0 → pure content (V1 TF-IDF). alpha=1 → pure collaborative (V2A SVD).
The UI slider puts "Content" on the left (0) and "Collaborative" on the
right (1), so alpha matches the slider position directly.

The score arrays cover different movie universes (V1: 16,556 English-language
films; V2A: 1,956 films in the bridged MovieLens set). We project both onto
the full catalog (~22,620 films): when one engine doesn't cover a movie, it
contributes 0 on that side instead of -inf — so a movie covered by only one
engine still ranks if its single side is strong enough.

Effective coverage: union of the two engines ≈ 16,800 unique films (74% of
the catalog), 8.6× wider than fold-in alone.

Each returned recommendation is paired with a "Because you saved X (sim Y.YY)"
explanation, computed via V1 cosine similarity even when the score blend
leaned CF — content similarity is more intuitive for end users.
"""
from typing import List

import numpy as np
import pandas as pd

from data_loader import movie_to_list_dict

from . import item_based, user_based


def _minmax(x: np.ndarray) -> np.ndarray:
    """Min-max normalize a 1-D vector to [0, 1].

    Returns zeros if the input has no positive variance — happens when content
    or CF contributes no signal at all (e.g. all liked films outside an engine).
    """
    if x.size == 0:
        return x
    lo = float(np.min(x))
    hi = float(np.max(x))
    if hi <= lo:
        return np.zeros_like(x, dtype=np.float32)
    return ((x - lo) / (hi - lo)).astype(np.float32)


def _build_content_scores(
    liked_ids: List[int], movies_df: pd.DataFrame
) -> "tuple[np.ndarray, list[int], list[int]]":
    """Return (catalog-wide content score vector, used_ids, ignored_ids).

    used_ids: liked films that are in V1's English subset.
    ignored_ids: liked films NOT in V1 (still might be served by CF).
    """
    catalog_size = len(movies_df)
    catalog_id_to_pos = {int(mid): i for i, mid in enumerate(movies_df["id"].values)}
    catalog_scores = np.zeros(catalog_size, dtype=np.float32)

    v1_ids = item_based.get_v1_tmdb_ids()  # aligned with V1 matrix rows

    used: List[int] = []
    ignored: List[int] = []
    for mid in liked_ids:
        sims = item_based.score_vector_for_seed(mid)
        if sims is None:
            ignored.append(mid)
            continue
        used.append(mid)
        # Sum into catalog-wide vector at each V1 row's catalog position.
        for v1_row, sim in enumerate(sims):
            if sim <= 0:
                continue
            pos = catalog_id_to_pos.get(int(v1_ids[v1_row]))
            if pos is not None:
                catalog_scores[pos] += float(sim)

    return _minmax(catalog_scores), used, ignored


def _build_cf_scores(
    liked_ids: List[int], movies_df: pd.DataFrame
) -> "tuple[np.ndarray, list[int], list[int]]":
    """Return (catalog-wide CF score vector, used_ids, ignored_ids).

    Uses user_based.fold_in_scores under the hood, then projects the SVD-set
    scores onto the full catalog.
    """
    catalog_size = len(movies_df)
    catalog_scores = np.zeros(catalog_size, dtype=np.float32)
    catalog_id_to_pos = {int(mid): i for i, mid in enumerate(movies_df["id"].values)}

    scores, _used_cols, used, ignored = user_based.fold_in_scores(liked_ids)
    if scores is None:
        return catalog_scores, used, ignored

    idx_to_tmdb = user_based._state["idx_to_tmdb"]
    for svd_col, tmdb_id in enumerate(idx_to_tmdb):
        pos = catalog_id_to_pos.get(int(tmdb_id))
        if pos is not None:
            catalog_scores[pos] = scores[svd_col]

    return _minmax(catalog_scores), used, ignored


def _build_explanations(
    rec_tmdb_ids: List[int], liked_ids: List[int]
) -> dict:
    """For each recommended id, find which liked film is most similar (V1 cosine).

    Uses V1 TF-IDF cosine similarity even if the score blend leaned CF —
    content similarity is more user-intuitive ("you liked X, this is similar
    to X"). Skips liked films that aren't in V1's English subset.
    """
    explanations: dict = {}
    if not liked_ids or not rec_tmdb_ids:
        return explanations

    # Pre-fetch each liked film's sim vector (in V1 row coordinates).
    liked_sims = []
    for mid in liked_ids:
        sims = item_based.score_vector_for_seed(mid)
        if sims is not None:
            liked_sims.append((mid, sims))
    if not liked_sims:
        return explanations

    v1_id_to_row = {int(mid): i for i, mid in enumerate(item_based.get_v1_tmdb_ids())}

    for rec_id in rec_tmdb_ids:
        rec_row = v1_id_to_row.get(int(rec_id))
        if rec_row is None:
            continue  # rec is not in V1 — leave it unexplained
        best_source = None
        best_sim = -1.0
        for source_id, sims in liked_sims:
            s = float(sims[rec_row])
            if s > best_sim:
                best_sim = s
                best_source = source_id
        if best_source is None or best_sim <= 0:
            continue
        explanations[int(rec_id)] = {
            "source_id": int(best_source),
            "source_title": item_based.get_v1_title(best_source) or "",
            "sim": round(best_sim, 3),
        }
    return explanations


def recommend(
    liked_movie_ids: List[int],
    n: int = 20,
    alpha: float = 0.5,
) -> dict:
    """Hybrid content + CF recommendation for a list of liked films.

    alpha = 0 → pure content (V1 TF-IDF aggregation).
    alpha = 1 → pure collaborative filtering (V2A SVD fold-in).
    Anything in between blends both signals.
    """
    if not liked_movie_ids:
        raise ValueError("liked_movie_ids must not be empty")

    alpha = float(max(0.0, min(1.0, alpha)))

    # Pull the catalog once via user_based's indexed movies_df (which is the
    # full movies dataframe set_index("id", drop=False) — handy lookup).
    movies_df = user_based._state["movies_df"]
    if movies_df is None:
        raise RuntimeError("user_recommender not built — cannot hybrid-recommend.")

    # Dedupe input while preserving order.
    seen = set()
    dedup_ids: List[int] = []
    for raw in liked_movie_ids:
        try:
            mid = int(raw)
        except (TypeError, ValueError):
            continue
        if mid in seen:
            continue
        seen.add(mid)
        dedup_ids.append(mid)
    if not dedup_ids:
        raise ValueError("no valid integer movie ids in input")

    content_scores, content_used, content_ignored = _build_content_scores(dedup_ids, movies_df)
    cf_scores, cf_used, cf_ignored = _build_cf_scores(dedup_ids, movies_df)

    # Effective coverage: union of films picked up by either engine.
    used_ids = sorted(set(content_used) | set(cf_used))
    ignored_ids = sorted(set(dedup_ids) - set(used_ids))

    if not used_ids:
        return {
            "recommendations": [],
            "used_ids": [],
            "ignored_ids": ignored_ids,
            "explanations": {},
            "hint": (
                "None of your saved films are in either recommender's index — "
                "try saving a few mainstream pre-2017 titles."
            ),
        }

    # alpha=0 → 1·content + 0·cf (plan UX: slider left = "Content").
    # alpha=1 → 0·content + 1·cf (slider right = "Collaborative").
    final = (1.0 - alpha) * content_scores + alpha * cf_scores

    # Mask out the liked films themselves.
    catalog_id_to_pos = {int(mid): i for i, mid in enumerate(movies_df["id"].values)}
    for mid in dedup_ids:
        pos = catalog_id_to_pos.get(mid)
        if pos is not None:
            final[pos] = -np.inf

    # Pick top-N from finite positions.
    finite_mask = np.isfinite(final) & (final > 0)
    finite_count = int(finite_mask.sum())
    if finite_count == 0:
        # Can happen at extreme alpha values when the dominant side has zero
        # signal (e.g. alpha=1 but all liked films are outside the SVD set).
        # Suggest moving toward whichever side actually has signal.
        content_has = bool(np.any(content_scores > 0))
        cf_has = bool(np.any(cf_scores > 0))
        if alpha >= 1.0 and content_has and not cf_has:
            side_hint = "Move the slider toward Content — these films aren't in the SVD index."
        elif alpha <= 0.0 and cf_has and not content_has:
            side_hint = "Move the slider toward Collaborative — these films aren't in the V1 content index."
        else:
            side_hint = "These films have no recommendation signal in either index."
        return {
            "recommendations": [],
            "used_ids": used_ids,
            "ignored_ids": ignored_ids,
            "explanations": {},
            "hint": f"No candidates at this slider position. {side_hint}",
        }

    n = max(1, min(int(n), finite_count))
    top = np.argpartition(-final, n - 1)[:n]
    top = top[np.argsort(-final[top])]

    # Serialize results.
    catalog_ids = movies_df["id"].to_numpy()
    rec_tmdb_ids = [int(catalog_ids[p]) for p in top]
    recommendations = []
    for tmdb_id in rec_tmdb_ids:
        try:
            row = movies_df.loc[int(tmdb_id)]
        except KeyError:
            continue
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        recommendations.append(movie_to_list_dict(row))

    explanations = _build_explanations(rec_tmdb_ids, used_ids)

    return {
        "recommendations": recommendations,
        "used_ids": used_ids,
        "ignored_ids": ignored_ids,
        "explanations": explanations,
    }
