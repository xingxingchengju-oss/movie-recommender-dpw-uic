"""Retry the tmdb_download_failures.log entries against TMDB's /tv/ endpoint.

About 130 of the 203 failures from the /movie/ endpoint are actually TV series
mis-classified as movies in the MovieLens dataset (e.g., London Spy, Planet
Earth, The Story of Film). TMDB serves them under /tv/{id} instead. This
script reads the failure log and tries each id against /tv/, then downloads
any poster that exists. Filenames stay `tt{imdb_id}.jpg` so they slot into
the same lookup data_loader._build_poster_lookup uses — no conflict with the
existing /movie/-sourced files.

Re-running is idempotent (skips files already on disk). Writes a new
tmdb_tv_download_failures.log with whatever still can't be found.
"""

import argparse
import concurrent.futures
import os
import time
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parent.parent
LINKS = BASE / "data" / "raw" / "links.csv"
OUT = BASE / "static" / "posters"
IN_LOG = BASE / "static" / "tmdb_download_failures.log"
OUT_LOG = BASE / "static" / "tmdb_tv_download_failures.log"

API_URL = "https://api.themoviedb.org/3/tv/{tid}"
CDN = "https://image.tmdb.org/t/p/w500"
UA = "Reelvana-UIC-CourseProject/1.0"
WORKERS = 16
TIMEOUT = 20
RATE_LIMIT_BACKOFF = 6.0
MAX_ATTEMPTS = 3


def build_jobs():
    if not IN_LOG.exists():
        raise SystemExit(f"no failure log at {IN_LOG} — run download_poster_tmdb.py first")
    failed_imdb = [
        line.split("\t")[0].replace(".jpg", "").replace("tt", "")
        for line in IN_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    links = pd.read_csv(LINKS, dtype={"imdbId": str, "tmdbId": str}, usecols=["imdbId", "tmdbId"])
    links = links.dropna(subset=["imdbId", "tmdbId"])
    imdb_to_tmdb = dict(zip(links["imdbId"], links["tmdbId"]))

    existing = {f for f in os.listdir(OUT) if f.endswith(".jpg")}

    jobs = []
    skipped_existing = 0
    skipped_no_map = 0
    for imdb_raw in failed_imdb:
        imdb = imdb_raw.zfill(7)
        tmdb = imdb_to_tmdb.get(imdb)
        if not tmdb:
            skipped_no_map += 1
            continue
        fname = f"tt{imdb}.jpg"
        if fname in existing:
            skipped_existing += 1
            continue
        jobs.append((tmdb, fname))

    print(f"[tv] failures from previous run: {len(failed_imdb)}")
    print(f"[tv] skipped - already on disk: {skipped_existing}")
    print(f"[tv] skipped - no imdb->tmdb map: {skipped_no_map}")
    print(f"[tv] to retry against /tv/ endpoint: {len(jobs)}")
    return jobs


def fetch(job, session, api_key):
    tmdb, fname = job
    dest = OUT / fname
    last_err = "unknown"
    for _ in range(MAX_ATTEMPTS):
        try:
            meta = session.get(API_URL.format(tid=tmdb), params={"api_key": api_key}, timeout=TIMEOUT)
            if meta.status_code == 429:
                last_err = "api HTTP 429"
                time.sleep(RATE_LIMIT_BACKOFF)
                continue
            if meta.status_code == 404:
                return (fname, False, "not on /tv/ either")
            if meta.status_code != 200:
                last_err = f"api HTTP {meta.status_code}"
                time.sleep(1.0)
                continue
            poster_path = meta.json().get("poster_path")
            if not poster_path:
                return (fname, False, "tv entry has no poster_path")
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


def main():
    parser = argparse.ArgumentParser(description="Retry failed posters via TMDB /tv/ endpoint.")
    parser.add_argument("--key", help="TMDB API key (or set env TMDB_API_KEY)")
    args = parser.parse_args()
    api_key = args.key or os.environ.get("TMDB_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("ERROR: no TMDB API key. Set env TMDB_API_KEY=... or pass --key XXX")

    jobs = build_jobs()
    total = len(jobs)
    if total == 0:
        print("[tv] nothing to do.")
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
    print(f"[tv] done in {(time.time()-t0):.1f}s. {total - len(failures)} ok, {len(failures)} still missing. log: {OUT_LOG}")


if __name__ == "__main__":
    main()
