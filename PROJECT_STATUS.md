# Reelvana — Project Status Report
**Course:** CST3104 Software Development Workshop II, UIC, Spring 2025-2026  
**Last Updated:** 2026-05-04  
**Purpose:** Onboarding snapshot for Claude project — reflects current repo state and completion plan.

---

## 1. Project Overview

Reelvana is a movie analytics & recommendation web app built on:
- **TMDB + MovieLens** data (≤ July 2017, no future data)
- **Stack:** Python 3.9+ · Flask · HTML/CSS/JS · pandas · scikit-learn · Plotly.js

**Four core pages:**
| Route | Page | Status |
|-------|------|--------|
| `/` | Movie List (browse + filter) | Frontend done, backend missing |
| `/movie/<id>` | Movie Detail | Frontend done, backend missing |
| `/analysis` | Analytics Dashboard | Frontend done with mock data, backend missing |
| `/recommender` | TF-IDF Recommendation | Not started |

---

## 2. Current File Structure

```
reelvana/
├── app.py                  ← EMPTY (0 bytes) — all Flask routes go here
├── config.py               ← EMPTY (0 bytes)
├── requirements.txt        ← EMPTY (0 bytes)
├── recommender.py          ← MISSING — TF-IDF + cosine similarity
├── analysis.py             ← MISSING — chart data functions
│
├── data/
│   ├── processed/          ← READ-ONLY, primary data source
│   │   ├── movies_final_clean.csv   ★ PRIMARY DATASET (22,720 raw rows; 22,620 used after dropping 7 CSV-corrupted rows; 22 cols)
│   │   ├── movies_clean.csv         (22,830 rows, near-identical, secondary)
│   │   ├── ratings_clean.csv        (40,009 rows: userId, movieId, rating)
│   │   ├── imdb_id.csv              (7,534 rows: imdb_id column, tt-format)
│   │   ├── Data Cleaning Pipeline.txt
│   │   └── data_quality_report.txt
│   └── raw/                ← ignored by git, do not modify
│       ├── links.csv        (45,844 rows: movieId, imdbId, tmdbId) ← IMDB bridge
│       ├── movies_metadata.csv
│       ├── ratings.csv      (26M rows — full dataset, too large to use directly)
│       ├── ratings_small.csv
│       ├── credits.csv, keywords.csv, links_small.csv
│       └── preprocess.py   (data cleaning script used to produce processed/)
│
├── docs/
│   ├── assignment/
│   │   └── GroupProject26.pdf       ← ASSIGNMENT REQUIREMENTS (read this first)
│   ├── analysis/
│   │   ├── q1.m                     ← MATLAB script: production trends + genre distribution
│   │   ├── q2.m                     ← MATLAB script: budget/revenue/ROI analysis
│   │   ├── q1/
│   │   │   ├── Movie Production Trend.pdf
│   │   │   ├── Genre Distribution Area Chart.pdf
│   │   │   └── Genre-Decade Heatmap.pdf
│   │   └── q2/
│   │       ├── Budget vs Revenue Regression.pdf
│   │       ├── Financial Correlation.pdf
│   │       └── ROI by Genre.pdf
│   ├── SoftwareDesignSpecification_1.3(4).docx
│   └── ui_reference/
│       └── figure_1.png, figure_5.jpeg, figure_11.jpeg, figure_14.jpeg,
│           figure_16.jpeg, figure_17.png  (UI mockup screenshots)
│
├── static/
│   ├── style.css            ← COMPLETE (dark theme, 20.7 KB)
│   ├── script.js            ← COMPLETE (filtering/sorting/rendering logic)
│   ├── mock_data.js         ← to be REMOVED once backend API is wired
│   └── posters/             ← 8,473 JPG poster images (git-ignored, ~600 MB)
│       └── tt{imdb_id}.jpg  (e.g. tt0114709.jpg = Toy Story)
│
├── templates/
│   ├── base.html            ← COMPLETE (sidebar layout, Lucide icons)
│   ├── movie_list.html      ← COMPLETE (genre filter, sort, card grid)
│   ├── movie_detail.html    ← COMPLETE (poster, stats, overview)
│   └── analysis.html        ← COMPLETE (4-tab Plotly dashboard, KPI cards)
│
└── notebooks/               (empty, reserved for EDA)
```

---

## 3. Primary Dataset Schema

### `data/processed/movies_final_clean.csv` (22,720 raw rows; 22,620 usable)
> **Note on row count:** `wc -l` reports 22,829 but that counts embedded newlines inside quoted `overview` fields. Python's csv module gives the true 22,720 logical rows. The loader drops 100 rows total: 7 with NaN title + 93 with column-shift corruption that left implausible values in place (vote_average > 10, garbled `�` titles, pure-numeric titles, or out-of-range years). Final usable count: **22,620** (0.44% data loss).
>
> **Open question (resolve in Phase 3):** Q1/Q2 MATLAB analysis was run on this same file. Verify whether MATLAB's `readtable` produced the same 22,620-row count or a different number (it may handle column-shifted rows differently). If the dashboard's totals don't match the q1/q2 PDFs by ±10 rows, this is the likely culprit.
| Column | Type | Notes |
|--------|------|-------|
| `id` | int | TMDB movie ID — primary key |
| `title` | str | Movie title |
| `release_year` | int | 1874–2017 |
| `release_decade` | int | 1870, 1880, …, 2010 |
| `primary_genre` | str | Single main genre |
| `genres_parsed` | str | Pipe-separated (e.g. `Animation\|Comedy\|Family`) |
| `overview` | str | Plot summary — used for TF-IDF |
| `keywords_parsed` | str | Pipe-separated keywords |
| `vote_average` | float | 0–10 |
| `vote_count` | int | |
| `director` | str | |
| `top_cast` | str | Pipe-separated top 5 actors |
| `budget` | float | NaN = undisclosed — **exclude from financial calcs** |
| `revenue` | float | NaN = undisclosed — **exclude from financial calcs** |
| `profit` | float | revenue − budget (NaN if either missing) |
| `roi` | float | (revenue−budget)/budget (NaN if either missing) |
| `runtime` | float | Minutes |
| `popularity` | float | TMDB popularity score |
| `original_language` | str | |
| `countries` | str | |
| `status` | str | Usually "Released" |

### `data/processed/ratings_clean.csv` (40,009 rows)
| Column | Notes |
|--------|-------|
| `userId` | 1–671 |
| `movieId` | MovieLens ID (≠ TMDB id) |
| `rating` | 0.5–5.0 |

> **Warning:** `ratings_clean.csv.movieId` is the **MovieLens** ID, not the TMDB `id` in movies_final_clean.csv. Bridge via `data/raw/links.csv` (movieId → imdbId → tmdbId).

### `data/processed/imdb_id.csv` (7,533 rows)
Single column `imdb_id` in `tt-format`. **Caveat:** this file is incomplete — it lists 7,533 entries but `static/posters/` actually contains 8,473 files. The loader uses `os.listdir(POSTERS_DIR)` directly as the existence check, ignoring `imdb_id.csv`, to avoid silently missing 943 posters.

### Poster Linkage Chain
```
movies_final_clean.csv[id] (TMDB)
  → data/raw/links.csv[tmdbId → imdbId]
  → static/posters/tt{imdbId}.jpg
```
Only **4,859 of the 22,620 movies** resolve to a poster on disk (the upper bound — many TMDB ids in our cleaned set don't appear in `data/raw/links.csv`, so they can't be linked to an IMDB id). The 8,473 poster files cover ~21% of the movie catalog. Fall back to gradient placeholder when poster is absent.

---

## 4. What's Complete

### Frontend (100%)
- **Dark theme UI** fully implemented in `style.css` — CSS variables, sidebar, card animations, custom dropdowns
- **Movie list page** — genre filter tags, sort by rating/date, card grid with gradient placeholders
- **Movie detail page** — poster area, metadata stats, overview text
- **Analysis dashboard** — 4 Plotly.js tabs (Production by Year, Genre Distribution, Top Directors, Rating Trends), KPI cards with entrance animation
- Currently powered by `mock_data.js` (25 hardcoded movies + mock chart data)

### Data & Analysis (100%)
- Cleaned datasets ready in `data/processed/`
- Q1 analysis complete (production trends, genre evolution by decade) — see `docs/analysis/q1/`
- Q2 analysis complete (budget vs revenue regression, ROI by genre, correlation heatmap) — see `docs/analysis/q2/`
- MATLAB source scripts in `docs/analysis/q1.m` and `q2.m`

---

## 5. What's Missing (Backend = 0%)

| File | What it needs to do |
|------|---------------------|
| `requirements.txt` | flask, pandas, scikit-learn, numpy |
| `app.py` | Flask routes: `/`, `/movie/<id>`, `/analysis`, `/api/movies`, `/api/recommend` |
| `recommender.py` | Load movies_final_clean.csv → TF-IDF on overview+genres_parsed+keywords_parsed → cosine similarity matrix → return top-N |
| `analysis.py` | Functions that read data and return JSON for each chart in analysis.html |

---

## 6. Key Design Constraints

- **Data cutoff:** All data ≤ July 2017. No external API calls needed.
- **Startup pre-compute:** TF-IDF matrix built once on `app.py` startup, held in memory. No database, no persistence.
- **NaN handling:** `budget=NaN` and `revenue=NaN` mean undisclosed — always exclude from financial stats.
- **One file per layer:** `app.py` (routes), `recommender.py` (ML), `analysis.py` (chart data). Don't split further.
- **Poster serving:** Flask serves `static/posters/tt{imdb_id}.jpg`. Fall back to CSS gradient when file missing.
- **No heavy deps:** pandas, scikit-learn, flask only. No database, no Celery, no Redis.

---

## 7. Completion Plan (Solo, ~3–4 Days)

### Day 1 — Backend Foundation
**Goal:** Flask app serving real data, movie list and detail pages functional.

1. Write `requirements.txt`:
   ```
   flask
   pandas
   scikit-learn
   numpy
   ```
2. Write `app.py` skeleton — load `movies_final_clean.csv` at startup into a pandas DataFrame.
3. Implement `GET /api/movies` — return paginated/filtered JSON from DataFrame.
4. Implement `GET /api/movie/<tmdb_id>` — return single movie JSON + poster URL.
5. Update `movie_list.html` and `movie_detail.html` to fetch from API instead of `mock_data.js`.
6. Add poster URL logic: check if `static/posters/tt{imdb_id}.jpg` exists via `data/raw/links.csv` join; fall back to gradient.

### Day 2 — Recommender
**Goal:** `/recommender` page returns real TF-IDF recommendations.

1. Write `recommender.py`:
   - Load `movies_final_clean.csv`
   - Build TF-IDF on `overview + " " + genres_parsed + " " + keywords_parsed`
   - Compute full cosine similarity matrix
   - Expose `get_recommendations(movie_id, n=10)` → list of movie dicts
2. Add `GET /api/recommend?id=<tmdb_id>&n=10` route in `app.py`.
3. Wire up frontend: search box on recommender page → call API → render card grid (reuse existing card HTML).

### Day 3 — Analysis Dashboard
**Goal:** `analysis.html` shows real data from `movies_final_clean.csv`.

1. Write `analysis.py` with functions mirroring the q1/q2 MATLAB analysis:
   - `production_by_decade()` → dict for bar chart
   - `genre_distribution()` → dict for pie/donut chart
   - `top_directors(n=10)` → dict for horizontal bar chart
   - `rating_trends_by_genre()` → dict for multi-line chart
   - `budget_revenue_scatter()` → dict for scatter (Q2)
   - `roi_by_genre()` → dict for box chart (Q2)
   - `financial_correlation()` → dict for heatmap (Q2)
2. Add `GET /api/analysis/<chart_name>` routes in `app.py`.
3. Update `analysis.html` to fetch from API instead of `CHART_DATA` mock object.
4. Update KPI cards (Total Movies, Avg Rating, Top Genre, Total Revenue) from real data.

### Day 4 — Polish & Wrapup
1. Remove `mock_data.js` from templates (or keep as fallback if no Flask running).
2. Add a simple text search on movie list page (filter by title).
3. Test all routes end-to-end.
4. Update `README.md` with run instructions (`pip install -r requirements.txt && python app.py`).
5. Verify `data/raw/` and `static/posters/` are git-ignored (confirmed in `.gitignore`).

---

## 8. Quick Reference — Data Loading Pattern

```python
# Standard pattern for app.py startup
import pandas as pd

df_movies = pd.read_csv('data/processed/movies_final_clean.csv')
df_ratings = pd.read_csv('data/processed/ratings_clean.csv')
df_links = pd.read_csv('data/raw/links.csv')  # movieId, imdbId, tmdbId

# Build TMDB id → imdb_id lookup for poster URLs
links_map = df_links.set_index('tmdbId')['imdbId'].to_dict()
# imdbId in links.csv is numeric; poster filenames use tt-format (zero-padded to 7 digits)
# e.g. imdbId=114709 → "tt0114709"
def get_poster_url(tmdb_id):
    imdb_num = links_map.get(tmdb_id)
    if imdb_num:
        return f"/static/posters/tt{int(imdb_num):07d}.jpg"
    return None  # frontend falls back to gradient
```

---

## 9. Files to Ignore / Not Modify

- `data/raw/` — raw source data, do not touch
- `data/processed/` — cleaned data, treat as read-only
- `static/posters/` — 8,473 images, git-ignored
- `docs/analysis/` — completed analysis artifacts for reference only
- `docs/SoftwareDesignSpecification_1.3(4).docx` — design doc
