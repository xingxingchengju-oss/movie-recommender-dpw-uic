"""Fill the static/posters/ folder with TMDB-hosted posters.

We can't use the 2017 movies_metadata.csv poster_path column because TMDB has
rotated ~83% of those CDN paths in the years since (verified by HEAD probe).
Instead, we query the live TMDB v3 API for each tmdb_id to get the CURRENT
poster_path, then download from image.tmdb.org.

Per job:
  1. Look up imdb_id from links.csv → target filename `tt{imdb_id}.jpg`.
  2. Skip if the file already exists.
  3. GET https://api.themoviedb.org/3/movie/{tmdb_id}?api_key=KEY → poster_path.
  4. GET https://image.tmdb.org/t/p/w500{poster_path} → save as the file.

API key resolution:
  - env var TMDB_API_KEY (preferred — keeps the key out of shell history)
  - CLI arg --key XXX (fallback)

Output:
  - JPEGs in static/posters/
  - tmdb_download_failures.log: tab-separated <filename>\\t<reason> for retry.

Re-running is idempotent: only still-missing files are attempted.
"""

import argparse
import concurrent.futures
import os
import time
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parent.parent
MOVIES = BASE / "data" / "processed" / "movies_final_clean.csv"
LINKS = BASE / "data" / "raw" / "links.csv"
OUT = BASE / "static" / "posters"
LOG = BASE / "static" / "tmdb_download_failures.log"

API_URL = "https://api.themoviedb.org/3/movie/{tid}"
CDN = "https://image.tmdb.org/t/p/w500"
UA = "Reelvana-UIC-CourseProject/1.0"
WORKERS = 24
TIMEOUT = 20
PER_REQUEST_DELAY = 0.0       # API tier allows ~50 req/s; no extra pacing needed
RATE_LIMIT_BACKOFF = 6.0      # wait this long if TMDB returns 429
MAX_ATTEMPTS = 3


def build_jobs():
    # movies_final_clean.csv has a few non-UTF-8 bytes from the cleaning pipeline
    # (same workaround as data_loader.py:45). We only read `id`, so replacing is safe.
    movies = pd.read_csv(MOVIES, usecols=["id"], encoding="utf-8", encoding_errors="replace")
    movies["id"] = pd.to_numeric(movies["id"], errors="coerce")
    movies = movies.dropna(subset=["id"])
    movie_ids = set(movies["id"].astype("int64").astype(str))

    links = pd.read_csv(
        LINKS,
        dtype={"imdbId": str, "tmdbId": str},
        usecols=["imdbId", "tmdbId"],
    )
    links = links.dropna(subset=["imdbId", "tmdbId"])
    tmdb_to_imdb = dict(zip(links["tmdbId"], links["imdbId"]))

    existing = {f for f in os.listdir(OUT) if f.endswith(".jpg")}

    jobs = []
    skipped_existing = 0
    skipped_no_imdb = 0
    for tmdb_id in movie_ids:
        imdb_id = tmdb_to_imdb.get(tmdb_id)
        if not imdb_id:
            skipped_no_imdb += 1
            continue
        fname = f"tt{imdb_id.zfill(7)}.jpg"
        if fname in existing:
            skipped_existing += 1
            continue
        jobs.append((tmdb_id, fname))

    print(f"[tmdb] movies in scope: {len(movie_ids)}")
    print(f"[tmdb] skipped - already on disk: {skipped_existing}")
    print(f"[tmdb] skipped - no imdb mapping: {skipped_no_imdb}")
    print(f"[tmdb] to fetch: {len(jobs)}")
    return jobs


def fetch(job, session, api_key):
    tmdb_id, fname = job
    dest = OUT / fname
    last_err = "unknown"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            if PER_REQUEST_DELAY:
                time.sleep(PER_REQUEST_DELAY)
            meta = session.get(API_URL.format(tid=tmdb_id), params={"api_key": api_key}, timeout=TIMEOUT)
            if meta.status_code == 429:
                last_err = "api HTTP 429"
                time.sleep(RATE_LIMIT_BACKOFF)
                continue
            if meta.status_code == 404:
                return (fname, False, "api HTTP 404 (movie not found)")
            if meta.status_code != 200:
                last_err = f"api HTTP {meta.status_code}"
                time.sleep(1.0)
                continue
            poster_path = meta.json().get("poster_path")
            if not poster_path:
                return (fname, False, "api returned no poster_path")
            img = session.get(CDN + poster_path, timeout=TIMEOUT, allow_redirects=True)
            if img.status_code == 429:
                last_err = "img HTTP 429"
                time.sleep(RATE_LIMIT_BACKOFF)
                continue
            if img.status_code == 200 and img.headers.get("content-type", "").startswith("image/"):
                dest.write_bytes(img.content)
                return (fname, True, None)
            last_err = f"img HTTP {img.status_code}"
            time.sleep(1.0)
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(1.0)
    return (fname, False, last_err)


def resolve_api_key(cli_key):
    key = cli_key or os.environ.get("TMDB_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "ERROR: no TMDB API key. Set env var TMDB_API_KEY=... or pass --key XXX"
        )
    return key


def main():
    parser = argparse.ArgumentParser(description="Fill static/posters/ via TMDB v3 API.")
    parser.add_argument("--key", help="TMDB API key (or set env TMDB_API_KEY)")
    args = parser.parse_args()
    api_key = resolve_api_key(args.key)

    jobs = build_jobs()
    total = len(jobs)
    if total == 0:
        print("[tmdb] nothing to do.")
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
            if i % 200 == 0 or i == total:
                rate = i / (time.time() - t0)
                eta_min = (total - i) / rate / 60 if rate > 0 else 0
                print(f"[tmdb] {i}/{total} ({len(failures)} failed) {rate:.1f}/s ETA {eta_min:.1f}min")

    LOG.write_text("\n".join(failures), encoding="utf-8")
    print(f"[tmdb] done in {(time.time()-t0)/60:.1f}min. {total - len(failures)} ok, {len(failures)} failed. log: {LOG}")


if __name__ == "__main__":
    main()
