# Reelvana — Project Status Report
**Course:** CST3104 Software Development Workshop II, UIC, Spring 2025-2026  
**Last Updated:** 2026-05-06  
**Status:** ✅ **V1 shipped** — all five phases complete (foundation, real-data wiring, dashboard, EDA notebook, polish + Popular ranking + search autocomplete)
**Purpose:** Onboarding snapshot for Claude project — reflects current repo state.

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

## 4. V1 Completion Status — ✅ Shipped

### Backend (`app.py` + `data_loader.py` + `analysis.py` + `recommender.py`)
- Flask app loads CSV at startup in ~3 seconds, builds in-memory DataFrame + poster lookup + Bayesian-weighted score column
- 9 API endpoints (genres, movies list with filter/sort/search/pagination, single-movie detail, 9 chart data, KPI summary)
- Recommender stub raises `NotImplementedError` — V2 placeholder route renders a "Coming in V2" card

### Frontend (`templates/` + `static/`)
- `mock_data.js` deleted; all data flows from real APIs
- Movie list: paginated grid, infinite scroll via IntersectionObserver, 4 sort modes (Normal / **Popular** / Rating / Date), genre tag filter, **live search dropdown** with debounce + AbortController + match highlighting + "View all N results" expansion
- Movie detail: Jinja-rendered, real poster or gradient fallback, all metadata fields
- Analysis: 9 Plotly charts in 3 thematic groups (Trends / Financials / Audience), per-group accent color, chip-style sub-tabs, Insight banner under each chart, section narrative on top
- Recommender: minimal placeholder card with V2 roadmap pill

### EDA notebook (`notebooks/eda.ipynb`)
- Re-implements Q1 + Q2 charts in matplotlib (6 figures)
- Imports from `analysis.py` — single source of truth, never drifts from dashboard
- Exports each figure as both PNG (300dpi for slides) + PDF (vector for report) into `notebooks/figures/`
- `plot_style.py` provides the dark theme + 3 palettes (categorical / sequential / diverging)

---

## 5. Key Implementation Decisions

- **Bayesian-weighted "Popular" sort** — IMDb formula `WR = v/(v+m)·R + m/(v+m)·C` with `C = global mean rating`, `m = 90th percentile vote_count`. Top 10 are mainstream classics (Shawshank, Godfather, Dark Knight, Pulp Fiction, Forrest Gump, …) instead of obscure documentaries with 5 votes.
- **Search architecture** — backend already exposes `?q=` on `/api/movies`. Frontend wraps it with 250ms debounce, AbortController to cancel stale requests, min-2-chars guard, dropdown with poster thumbnails + match highlighting, ESC/click-outside to close.
- **Chart data layer purity** — `analysis.py` returns plain dicts, never Plotly/matplotlib config. Decouples calculation from visualization, lets dashboard (Plotly.js) and notebook (matplotlib) share the same logic.
- **Data filters** — Genre Evolution / Heatmap drop decades < 50 films (avoid 100% blocks from 1-3 film samples). Rating Trend drops decades < 20 films. ROI by Genre filters to ROI ≥ 1.0 (broke-even and above) for log-scale legibility. All filters declared in function defaults so notebook + dashboard agree.

---

## 6. V2 Roadmap

| Feature | What changes |
|---------|--------------|
| TF-IDF recommender | Implement `recommender.py:get_recommendations()`, wire `/api/recommend?id=<tmdb_id>&n=10`, replace placeholder card with similar-films grid on movie detail page |
| User auth + ratings history | Bind anonymous ratings (`ratings_clean.csv`) to login, expose "your taste profile" in dashboard |
| Frontend redesign | V1 prioritizes data correctness; V2 will revamp visual hierarchy + transitions |
| Real-time TMDB API | Optional supplement — current dataset is frozen ≤ July 2017 |

---

## 7. Files to Ignore / Not Modify

- `data/raw/` — raw source data, git-ignored, do not touch
- `data/processed/` — cleaned data, treat as read-only
- `static/posters/` — 8,473 images, git-ignored, ~600MB
- `docs/analysis/` — team's MATLAB Q1/Q2 baseline (kept as visual comparison)
- `docs/SoftwareDesignSpecification_1.3(4).docx` — design doc
