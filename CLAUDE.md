# Reelvana — Claude Code Guide

UIC sophomore group project (CST3104). Movie recommendation web app on TMDB + MovieLens data (≤ July 2017). Keep it simple — this is a course assignment, not production.

## Stack
Python 3.9+ · Flask · HTML/CSS/JS · pandas · scikit-learn · Plotly.js

## Structure
- `app.py` — all Flask routes (one file)
- `recommender.py` — TF-IDF + cosine similarity
- `analysis.py` — chart data functions
- `templates/` — HTML files
- `static/style.css` + `static/script.js` — one of each
- `data/` — movies_clean.csv, ratings_clean.csv (read-only)

## Data
- `movies_clean.csv` (22,796 rows): use `id`, `title`, `release_year`, `primary_genre`, `genres_parsed`, `overview`, `vote_average`, `keywords_parsed`, `director`
- `ratings_clean.csv` (40,008 rows): `userId`, `movieId`, `rating`
- `budget=NaN` / `revenue=NaN` mean undisclosed — exclude from financial calcs

## Recommendation
TF-IDF on `overview + genres_parsed + keywords_parsed`, cosine similarity, return top-N. Compute once at app startup, store in memory. No persistence needed.

## Rules
- All code/comments in English
- Don't modify files in `data/`
- Don't commit API keys
- Keep functions small and readable

## Workflow
Per task: state what file to change → write code → run `python app.py` to verify → done. Ask before changing data files or adding heavy dependencies.

See `docs/sds_v1.3` for UI mockups.
