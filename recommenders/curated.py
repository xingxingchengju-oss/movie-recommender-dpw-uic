"""Five curated MovieLens users for the 'Recommend for User' demo.

Picks chosen via scripts/pick_curated_users.py — multi-label genre attribution
over each user's bridged (MovieLens -> TMDB) ratings. Each user has >= 50
linked ratings, and the listed top-genre share is sharply differentiated so the
demo shows visibly different recommendation slates per profile.
"""

CURATED_USERS = [
    {"id":  41, "label": "Sci-fi enthusiast", "top_genre": "Science Fiction", "n_ratings":  71, "genre_share": 0.66},
    {"id": 239, "label": "Comedy fan",        "top_genre": "Comedy",          "n_ratings": 117, "genre_share": 0.88},
    {"id": 493, "label": "Romance lover",     "top_genre": "Romance",         "n_ratings":  58, "genre_share": 0.79},
    {"id":  95, "label": "Horror buff",       "top_genre": "Horror",          "n_ratings": 114, "genre_share": 0.40},
    {"id": 525, "label": "Action junkie",     "top_genre": "Action",          "n_ratings":  60, "genre_share": 0.53},
]
