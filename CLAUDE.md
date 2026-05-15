# Reelvana — Claude Code Guide

UIC sophomore group project (CST3104). Movie recommendation web app on TMDB + MovieLens data (≤ July 2017). Keep it simple — this is a course assignment, not production.

## Stack
Python 3.9+ · Flask · HTML/CSS/JS · pandas · scikit-learn · Plotly.js

## Structure
- `app.py` — all Flask routes (one file)
- `data_loader.py` — CSV ingest + per-row serializers used by every route
- `analysis.py` — chart data functions
- `recommenders/` — recommendation engines (package)
  - `item_based.py` — TF-IDF + cosine similarity (movie -> movie, V1)
  - `user_based.py` — SVD collaborative filtering (user -> movie, V2A)
  - `curated.py` — 5 hand-picked MovieLens user profiles for the demo
- `templates/` — Jinja HTML (sidebar lives in `_sidebar.html`, included by every page)
- `static/`
  - `style.css` — single stylesheet
  - `script.js` — page-specific IIFEs (movie grid, recommender tabs, homepage strip, predicted rating)
  - `user_profile.js` — global "Viewing As" state + sidebar UI (loaded on every page)
- `data/` — movies_final_clean.csv, ratings_clean.csv (read-only)
- `scripts/` — one-shot offline tools (curated-user picker, recommender eval)

## Data
- `movies_clean.csv` (22,796 rows): use `id`, `title`, `release_year`, `primary_genre`, `genres_parsed`, `overview`, `vote_average`, `keywords_parsed`, `director`
- `ratings_clean.csv` (40,008 rows): `userId`, `movieId`, `rating`
- `budget=NaN` / `revenue=NaN` mean undisclosed — exclude from financial calcs

## Recommendation
TF-IDF on `overview + genres_parsed + keywords_parsed`, cosine similarity, return top-N. Compute once at app startup, store in memory. No persistence needed.

## V2A: User Recommender (SVD collaborative filtering)
SVD via `scipy.sparse.linalg.svds`, k=50, with **user-mean centering** before factorization. The dense predicted-ratings matrix (671 users × 1956 movies, float32) is built at app startup in `user_recommender.py` and cached in memory; per-request work is a row copy + seen-mask + top-N argpartition. Ratings come from `ratings_clean.csv`; the MovieLens `movieId` is bridged to our TMDB `id` via `data/raw/links.csv` (MovieLens 1 = TMDB 862 = Toy Story — naive matching would be wrong).

**API:** `GET /api/users` lists profiles; `GET /api/recommend/user/<id>?n=20` returns recs in the same shape as V1's `/api/recommend/<movie_id>`.

**Curated user profiles** (picked via `scripts/pick_curated_users.py` — multi-label genre attribution over each user's bridged ratings, `≥50` ratings, top-genre share `≥0.40`):
| ID  | Label              | Top genre        | Ratings | Share |
|-----|--------------------|------------------|---------|-------|
| 41  | Sci-fi enthusiast  | Science Fiction  | 71      | 66%   |
| 239 | Comedy fan         | Comedy           | 117     | 88%   |
| 493 | Romance lover      | Romance          | 58      | 79%   |
| 95  | Horror buff        | Horror           | 114     | 40%   |
| 525 | Action junkie      | Action           | 60      | 53%   |

**Evaluation** (`scripts/eval_recommender.py`, 80/20 random split, seed=42):
- RMSE = 0.9552 · MAE = 0.7452 (on 7,796 servable test pairs)
- Precision@10 = 0.0983 (averaged over 287 users with ≥5 liked test ratings)
- Random baseline P@10 ≈ 0.003 — SVD is ~30× better than random.

## Rules
- All code/comments in English
- Don't modify files in `data/`
- Don't commit API keys
- Keep functions small and readable

## Workflow
Per task: state what file to change → write code → run `python app.py` to verify → done. Ask before changing data files or adding heavy dependencies.

See `docs/sds_v1.3` for UI mockups.
