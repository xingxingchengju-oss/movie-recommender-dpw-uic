"""Last-resort retry: TMDB IDs in the MovieLens dataset that no longer exist.

After /movie/ and /tv/ rounds, ~126 ids still 404. Spot-checking shows TMDB
*does* have the entries — under different ids (e.g. London Spy: dataset has
370722, live id is 64383). We search by title+year and match conservatively
to recover them.

Match rule (deliberately strict to avoid wrong-movie posters):
  - normalize title (lowercase, strip punctuation, collapse whitespace)
  - year must be within ±1 of the dataset year (release_date / first_air_date)
  - if no candidate matches both, give up (don't pick "best guess")

Output filenames stay `tt{imdb_id}.jpg`, so data_loader's existing lookup picks
them up after a Flask restart. Idempotent.
"""

import argparse
import concurrent.futures
import os
import re
import time
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parent.parent
MOVIES = BASE / "data" / "processed" / "movies_final_clean.csv"
LINKS = BASE / "data" / "raw" / "links.csv"
OUT = BASE / "static" / "posters"
OUT_LOG = BASE / "static" / "tmdb_search_download_failures.log"

SEARCH_URL = "https://api.themoviedb.org/3/search/multi"
CDN = "https://image.tmdb.org/t/p/w500"
UA = "Reelvana-UIC-CourseProject/1.0"
WORKERS = 12
TIMEOUT = 20
RATE_LIMIT_BACKOFF = 6.0
MAX_ATTEMPTS = 3


def normalize(t):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", str(t).lower())).strip()


def build_jobs():
    # Movies in scope = those in final clean whose poster file does NOT yet exist.
    movies = pd.read_csv(
        MOVIES,
        usecols=["id", "title", "release_year"],
        encoding="utf-8", encoding_errors="replace",
    )
    movies["id"] = pd.to_numeric(movies["id"], errors="coerce")
    movies["release_year"] = pd.to_numeric(movies["release_year"], errors="coerce")
    movies = movies.dropna(subset=["id", "title"])

    links = pd.read_csv(LINKS, dtype={"imdbId": str, "tmdbId": str}, usecols=["imdbId", "tmdbId"])
    links = links.dropna(subset=["imdbId", "tmdbId"])
    tmdb_to_imdb = dict(zip(links["tmdbId"], links["imdbId"]))

    existing = {f for f in os.listdir(OUT) if f.endswith(".jpg")}

    jobs = []
    for _, r in movies.iterrows():
        tmdb = str(int(r["id"]))
        imdb = tmdb_to_imdb.get(tmdb)
        if not imdb:
            continue
        fname = f"tt{imdb}.jpg"
        if fname in existing:
            continue
        year = int(r["release_year"]) if pd.notna(r["release_year"]) else None
        jobs.append((fname, r["title"], year))

    print(f"[search] still-missing posters in scope: {len(jobs)}")
    return jobs


def fetch(job, session, api_key):
    fname, title, year = job
    norm_title = normalize(title)
    last_err = "no match"
    for _ in range(MAX_ATTEMPTS):
        try:
            params = {"api_key": api_key, "query": title, "include_adult": "false"}
            if year:
                params["year"] = year
            r = session.get(SEARCH_URL, params=params, timeout=TIMEOUT)
            if r.status_code == 429:
                last_err = "search 429"
                time.sleep(RATE_LIMIT_BACKOFF)
                continue
            if r.status_code != 200:
                last_err = f"search HTTP {r.status_code}"
                time.sleep(1.0)
                continue
            picked = None
            for item in r.json().get("results", []):
                mt = item.get("media_type")
                if mt not in ("movie", "tv"):
                    continue
                cand_name = item.get("title") or item.get("name") or ""
                cand_date = item.get("release_date") or item.get("first_air_date") or ""
                cand_year = int(cand_date[:4]) if cand_date[:4].isdigit() else None
                if normalize(cand_name) != norm_title:
                    continue
                if year and cand_year and abs(cand_year - year) > 1:
                    continue
                if not item.get("poster_path"):
                    continue
                picked = item
                break
            if not picked:
                return (fname, False, "no exact title+year match")

            img = session.get(CDN + picked["poster_path"], timeout=TIMEOUT, allow_redirects=True)
            if img.status_code == 429:
                last_err = "img 429"
                time.sleep(RATE_LIMIT_BACKOFF)
                continue
            if img.status_code == 200 and img.headers.get("content-type", "").startswith("image/"):
                (OUT / fname).write_bytes(img.content)
                return (fname, True, None)
            last_err = f"img HTTP {img.status_code}"
            time.sleep(1.0)
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(1.0)
    return (fname, False, last_err)


def main():
    parser = argparse.ArgumentParser(description="Recover missing posters via TMDB /search/.")
    parser.add_argument("--key", help="TMDB API key (or set env TMDB_API_KEY)")
    args = parser.parse_args()
    api_key = args.key or os.environ.get("TMDB_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("ERROR: no TMDB API key. Set env TMDB_API_KEY=... or pass --key XXX")

    jobs = build_jobs()
    total = len(jobs)
    if total == 0:
        print("[search] nothing to do.")
        return

    failures = []
    t0 = time.time()
    with requests.Session() as s, concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        s.headers["User-Agent"] = UA
        futures = [pool.submit(fetch, j, s, api_key) for j in jobs]
        for i, fut in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                fname, ok, err = fut.result()
            except Exception as e:
                fname, ok, err = ("<unknown>", False, f"future crashed: {e}")
            if not ok:
                failures.append(f"{fname}\t{err}")

    OUT_LOG.write_text("\n".join(failures), encoding="utf-8")
    print(f"[search] done in {time.time()-t0:.1f}s. {total - len(failures)} ok, {len(failures)} still missing. log: {OUT_LOG}")


if __name__ == "__main__":
    main()
