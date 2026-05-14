# Legacy IMDb Selenium Crawler (archived)

These files implement the original poster-fetch pipeline:

```
crawler_poster_url.py  →  url_db.py (sqlite)  →  download_poster.py  →  static/posters/
       ↑                          ↑
browser_driver.py        imdb_posters_url(1).db
                         imdb_posters_url.csv
```

It was replaced because:

1. **Slow.** Selenium + IMDb anti-bot → ~3s/movie, ~12+ hours for the full ~22k-movie dataset.
2. **Incomplete input.** `data/processed/imdb_id.csv` only listed 7,533 of the ~22,720 movies that actually need posters.
3. **Required Chrome/Edge driver** with a hardcoded path (`D:\edgedriver_win64\msedgedriver.exe`).

The current pipeline lives in `static/`:

- `download_poster_tmdb.py` — TMDB v3 API `/movie/` endpoint (the main bulk run).
- `download_poster_tmdb_tv.py` — `/tv/` endpoint retry for TV series misclassified as movies.
- `download_poster_tmdb_search.py` — `/search/multi` fallback for ids the dataset has wrong.

Combined coverage: 22,596 / 22,620 = **99.89%** in ~12 minutes.

## Running anything in here

These scripts read CSVs from `static/` cwd (e.g. `download_poster.py` does
`pd.read_csv("imdb_posters_url.csv")`). To run them now:

```bash
cd static/_legacy_imdb_crawler
python crawler_poster_url.py      # needs Selenium + Edge driver
python download_poster.py         # needs imdb_posters_url.csv in cwd (already here)
```

Dependencies (separate from the project's root `requirements.txt`):

```
pip install -r requirements.txt   # selenium, webdriver-manager, beautifulsoup4
```

## Why keep instead of delete?

Coursework artifact — the IMDb crawler was the team's first iteration and
demonstrates a different scraping approach. Disk cost is ~600 KB. Safer to
archive than to lose history.
