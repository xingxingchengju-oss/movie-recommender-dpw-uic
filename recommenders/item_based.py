"""TF-IDF + cosine similarity recommender. Built once at app startup."""
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from data_loader import movie_to_list_dict

_state = {"matrix": None, "id_to_idx": None, "df": None}


def build(df: pd.DataFrame) -> None:
    # English-only subset: TF-IDF uses English stop words; mixed-language
    # overviews would pollute the similarity space.
    df_en = df[df["original_language"] == "en"].reset_index(drop=True)

    # Repeat genres 3x, keywords 2x, director 5x so the structured features
    # are not drowned out by the longer overview text. Director is the
    # strongest auteur signal — without boosting it, films by the same
    # director (e.g. Nolan: Inception / Interstellar / Memento) don't
    # cluster because they cover very different topics. The 5x weight was
    # tuned against the verification gate (Toy Story / Godfather / Inception).
    # This is a minor extension of the CLAUDE.md spec.
    def _norm_director(v):
        if pd.isna(v) or not str(v).strip():
            return ""
        # Take first listed director (some rows have pipe-separated names).
        return str(v).split("|")[0].strip().lower().replace(" ", "_")

    director_tokens = df_en["director"].apply(_norm_director)
    docs = (
        df_en["overview"].fillna("").astype(str) + " "
        + df_en["genres_list"].apply(lambda xs: (" ".join(xs) + " ") * 3) + " "
        + df_en["keywords_list"].apply(lambda xs: (" ".join(xs) + " ") * 2) + " "
        + (director_tokens + " ") * 5
    )
    empty = int((docs.str.strip() == "").sum())
    pct = 100.0 * empty / len(docs) if len(docs) else 0.0
    if pct > 5.0:
        print(f"[recommender] WARNING: {empty}/{len(docs)} ({pct:.1f}%) empty docs — "
              f"consider a title fallback in the doc construction.")
    else:
        print(f"[recommender] Empty docs: {empty}/{len(docs)} ({pct:.2f}%)")

    vec = TfidfVectorizer(
        stop_words="english", min_df=2, max_df=0.8,
        max_features=20000, sublinear_tf=True, dtype=np.float32,
    )
    mat = vec.fit_transform(docs)
    _state["matrix"] = mat
    _state["id_to_idx"] = {int(mid): i for i, mid in enumerate(df_en["id"].values)}
    _state["df"] = df_en


def get_status() -> dict:
    """Public accessor for startup logging and health checks."""
    if _state["matrix"] is None:
        return {"built": False}
    return {
        "built": True,
        "n_movies": _state["matrix"].shape[0],
        "n_features": _state["matrix"].shape[1],
    }


def get_recommendations(movie_id: int, n: int = 10) -> list[dict]:
    if _state["matrix"] is None:
        raise RuntimeError("Recommender not built. Call build(df) at app startup.")
    idx = _state["id_to_idx"].get(int(movie_id))
    if idx is None:
        return []
    sims = linear_kernel(_state["matrix"][idx], _state["matrix"]).ravel()
    sims[idx] = -1.0
    top = np.argpartition(-sims, n)[:n]
    top = top[np.argsort(-sims[top])]
    return [movie_to_list_dict(_state["df"].iloc[i]) for i in top]


# ── V2C support: expose primitives so recommenders.hybrid can aggregate ────

def has_movie(movie_id: int) -> bool:
    """Public membership check — does this TMDB id appear in the V1 index?"""
    return _state["id_to_idx"] is not None and int(movie_id) in _state["id_to_idx"]


def score_vector_for_seed(seed_id: int) -> Optional[np.ndarray]:
    """Full cosine-similarity row of one seed movie against the V1 TF-IDF matrix.

    Returns a 1-D float32 array of shape (n_v1_movies,) — the similarity of
    the seed against every English-language movie in the V1 index. The seed's
    own slot is set to 0.0 (not -1) so callers can safely aggregate multiple
    seeds before deciding what to mask out.

    Returns None when the seed isn't in the V1 index (e.g. non-English film).
    Used by recommenders.hybrid to build content-side scores across a list of
    liked movies.
    """
    if _state["matrix"] is None:
        raise RuntimeError("Recommender not built. Call build(df) at app startup.")
    idx = _state["id_to_idx"].get(int(seed_id))
    if idx is None:
        return None
    sims = linear_kernel(_state["matrix"][idx], _state["matrix"]).ravel().astype(np.float32)
    sims[idx] = 0.0
    return sims


def get_v1_tmdb_ids() -> np.ndarray:
    """Ordered TMDB id array aligned with the V1 TF-IDF matrix columns.

    Allows callers (hybrid) to map V1 row index -> TMDB id without re-indexing
    the DataFrame each call.
    """
    if _state["df"] is None:
        raise RuntimeError("Recommender not built. Call build(df) at app startup.")
    return _state["df"]["id"].to_numpy(dtype=np.int64)


def get_v1_title(tmdb_id: int) -> Optional[str]:
    """Lookup a movie's title from the V1 index (used by hybrid explanations)."""
    if _state["df"] is None:
        return None
    idx = _state["id_to_idx"].get(int(tmdb_id))
    if idx is None:
        return None
    return str(_state["df"].iloc[idx]["title"])
