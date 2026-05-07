"""Reelvana V2 stub — recommender system.

V1 ships without an active recommender; the page is a placeholder.

V2 plan: TF-IDF on (overview + genres_parsed + keywords_parsed) → cosine
similarity matrix → return top-N. Compute once at startup, hold in memory.
See PROJECT_STATUS.md for context.
"""


def get_recommendations(movie_id: int, n: int = 10) -> list[dict]:
    raise NotImplementedError(
        "Recommender V2 — not implemented in V1. See PROJECT_STATUS.md."
    )
