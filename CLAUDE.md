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
- `movies_final_clean.csv` (22,720 raw rows → **22,620 served**): use `id`, `title`, `release_year`, `primary_genre`, `genres_parsed`, `overview`, `vote_average`, `keywords_parsed`, `director`. The 100-row gap is the runtime sanity filter in `data_loader.py` dropping CSV column-shift corruption (7 NaN id/title + 8 out-of-range vote_average + 8 out-of-range release_year + 85 rows whose title is `�`-garbled or pure numerics).
- `ratings_clean.csv` (40,008 rows): `userId`, `movieId`, `rating`
- `budget=NaN` / `revenue=NaN` mean undisclosed — exclude from financial calcs

## Recommendation
TF-IDF on `overview + genres_parsed + keywords_parsed`, cosine similarity, return top-N. Compute once at app startup, store in memory. No persistence needed.

## V2A: User Recommender (SVD collaborative filtering)
SVD via `scipy.sparse.linalg.svds`, k=50, with **user-mean centering** before factorization. The dense predicted-ratings matrix (671 users × 1956 movies, float32) is built at app startup in `recommenders/user_based.py` and cached in memory; per-request work is a row copy + seen-mask + top-N argpartition. Ratings come from `ratings_clean.csv`; the MovieLens `movieId` is bridged to our TMDB `id` via `data/raw/links.csv` (MovieLens 1 = TMDB 862 = Toy Story — naive matching would be wrong). The predicted rating is stored on the MovieLens 0.5–5.0 scale; the Movie Detail page rescales it to /10 at display time so it sits side-by-side with the TMDB `vote_average`.

**API:** `GET /api/users` lists profiles; `GET /api/recommend/user/<id>?n=20` returns recs in the same shape as V1's `/api/recommend/<movie_id>`.

**Curated user profiles** (picked via `scripts/pick_curated_users.py` — multi-label genre attribution over each user's bridged ratings, `≥50` ratings, top-genre share `≥0.40`):
| ID  | Label              | Top genre        | Ratings | Share |
|-----|--------------------|------------------|---------|-------|
| 41  | Sci-fi enthusiast  | Science Fiction  | 71      | 66%   |
| 239 | Comedy fan         | Comedy           | 117     | 88%   |
| 493 | Romance lover      | Romance          | 58      | 79%   |
| 95  | Horror buff        | Horror           | 114     | 40%   |
| 525 | Action junkie      | Action           | 60      | 53%   |

**Honest note on the Horror buff (defense-relevant).** User 95 is the highest-share horror rater available in MovieLens-1M's 671 users — every other horror-leaning user sits at ≤28% share. With only 40% of their ratings on horror, SVD's latent factors capture the *other 60%* of their taste too (drama, thrillers, classics), so the recommendation slate mixes horror with broader picks rather than returning pure horror. We deliberately do **not** patch this with a hand-tuned genre boost — that would corrupt the "this is what SVD says" narrative. The honest framing is that V2C's hybrid α slider is the proper user-facing answer: drag toward Content to lean into genre fidelity for the films saved on the favorites list. Pure-SVD recommendations on a 671-user catalog will always drift toward popular cross-genre items; that's a property of CF on small data, not a bug.

**Evaluation** (`scripts/eval_recommender.py`, 80/20 random split, seed=42):
- RMSE = 0.9552 · MAE = 0.7452 (on 7,796 servable test pairs)
- Precision@10 = 0.0983 (averaged over 287 users with ≥5 liked test ratings)
- Random baseline P@10 ≈ 0.003 — SVD is ~30× better than random.

## V2B3: SVD fold-in (kept as the CF leg of V2C hybrid)
Fold-in projects a sparse synthetic rating vector into the SVD basis learned at startup. For training factors `R_centered ≈ U Σ Vt` and a synthetic centered vector `r_centered` (5.0 minus training-set global mean μ, only on selected movies):

```
u_new  = r_centered @ V / σ_safe         # project (σ_safe = max(σ, 1e-6))
scores = (u_new * σ) @ Vt + μ            # reconstruct
```

The σ in the projection and the σ in the reconstruction cancel mathematically (`r @ V Vt + μ` is equivalent), but we keep the two-step form because (a) it documents the algorithm step-by-step for the defense, and (b) the σ_safe floor guards against numerical noise from any tiny singular values.

**Baseline choice.** The synthetic user can't center against its own all-5.0 inputs (that collapses `r_centered` to zero). We use the training-set global mean (μ ≈ 3.57) — standard fold-in practice.

**State added at build time:** `Vt` (k×n_movies f32 ≈ 400 KB), `σ` (k float32 vector), `global_mean`.

**Public function:** `recommenders.user_based.fold_in_scores(liked_ids)` returns the raw (n_movies,) score vector plus used/ignored id lists. Used both by `recommend_from_synthetic_user` (internal) and by `recommenders.hybrid` (V2C).

## V2C: Favorites + Hybrid recommender
The original Build Your Own's temporary-input UX was replaced with **persistent favorites**:

- **Save button** on every Movie Detail page writes to `localStorage["reelvana_favorites"]` as `[{id, title}, ...]`.
- **Sidebar "Your favorites"** shows live count badge across all pages (`static/favorites.js`).
- **Recommend → From Favorites tab** has three states:
  - Curated profile active → "Switch to Guest" CTA (favorites are Guest-only by product design — avoids concept clash with curated profiles' 50+ MovieLens ratings).
  - Guest + 0 favorites → "Save a film on a detail page" empty state.
  - Guest + favorites → chips + **α slider** + Find button.

**Hybrid algorithm** (`recommenders/hybrid.py`): for liked ids `L`, computes two parallel catalog-wide score vectors and linearly blends:

```
content[m] = Σ_{l ∈ L} V1_cosine_sim(l, m)   # then min-max normalized to [0,1]
cf[m]      = SVD fold-in scores for L         # then min-max normalized to [0,1]
final[m]   = (1 - α) · content[m] + α · cf[m]
```

- α = 0 → pure content (V1 TF-IDF aggregation, covers 16,556 English films)
- α = 1 → pure CF (V2A SVD fold-in, covers 1,956 films)
- Anywhere in between blends both signals over the **union ≈ 16,800 films** = **~74% of the catalog**, vs fold-in alone at 8.6%.

A movie missing from one engine contributes 0 there (not -∞) so it still ranks if the other side scores it highly. Liked films are masked out before top-N.

**Why-this explanations.** Each returned recommendation includes `{source_id, source_title, sim}` — the liked film with highest V1 cosine similarity to that recommendation. Content-based attribution is more intuitive for end users than CF latent distance, even when the score blend leaned CF.

**API:** `POST /api/recommend/build` body `{movie_ids: int[], alpha?: float ∈ [0,1], n?: int}` returns `{recommendations, used_ids, ignored_ids, explanations}` (plus a friendly `hint` when the slider position kills all candidates).

**Known limitations** (for the defense):
- Favorites are local-storage-only — no cross-device sync.
- Hybrid uses simple min-max normalization rather than RRF or z-score; stable on small data, but α's meaning may drift slightly across queries.
- Why-this uses V1 cosine even for CF-heavy blends — UX choice, not bug.
- Favorites are Guest-only by design (curated profiles already have implicit "favorites" via their 50+ MovieLens ratings).

## Rules
- All code/comments in English
- Don't modify files in `data/`
- Don't commit API keys
- Keep functions small and readable

## Workflow
Per task: state what file to change → write code → run `python app.py` to verify → done. Ask before changing data files or adding heavy dependencies.

See `docs/sds_v1.3` for UI mockups.
