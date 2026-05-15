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

DEBUG = True
HOST = "127.0.0.1"
PORT = 5000
