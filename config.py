import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

MOVIES_CSV = BASE_DIR / "data" / "processed" / "movies_final_clean.csv"
RATINGS_CSV = BASE_DIR / "data" / "processed" / "ratings_clean.csv"
LINKS_CSV = BASE_DIR / "data" / "raw" / "links.csv"
IMDB_ID_CSV = BASE_DIR / "data" / "processed" / "imdb_id.csv"
POSTERS_DIR = BASE_DIR / "static" / "posters"

POSTER_URL_PREFIX = "/static/posters"

PER_PAGE_DEFAULT = 24
PER_PAGE_MAX = 100

# Debug off by default — flip on for local dev with `FLASK_DEBUG=1 python app.py`.
# Production / grading-machine runs must stay off (Werkzeug's debug console is
# remote-code-execution-capable when enabled on a network-reachable host).
DEBUG = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
HOST = "127.0.0.1"
PORT = 5000
