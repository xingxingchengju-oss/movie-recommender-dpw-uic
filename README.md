# 🎬 Reelvana

> Movie analytics & discovery web app — built on TMDB + MovieLens (≤ July 2017).

Group project for **CST3104 Software Development Workshop II** at United International College, Spring 2025-2026.

---

## ✨ V1 Features

- **Browse 22,620 films** — paginated grid (24/page), genre filtering, four sort modes:
  - **Normal** — original dataset order
  - **Popular** — IMDb-style **Bayesian-weighted score** (highly rated AND widely voted)
  - **Rating** — raw `vote_average` descending (warning: surfaces obscure films with few votes)
  - **Date** — release year descending
- **Live search with autocomplete dropdown** — debounced 250ms, AbortController-cancelled, top 5 hits with poster + year + rating, "View all N results →" expands to grid
- **Movie detail pages** — poster (4,859 of 22,620 films have real posters; rest get a deterministic gradient placeholder), full metadata, overview, top cast, director, financial facts
- **9-chart analytics dashboard** at `/analysis`, organized in three thematic groups:
  - **Trends (Q1)** — Production trend by decade · Genre evolution (% stacked) · Genre × decade heatmap
  - **Financials (Q2)** — Budget vs revenue (log-log + regression) · ROI by genre (log box plot) · Pearson correlation matrix
  - **Audience (Q3)** — Rating distribution · Rating trend by decade · Rating by genre
- **EDA notebook** at `notebooks/eda.ipynb` — reproducible matplotlib re-renders of Q1 + Q2 charts, exports 6 PNG (300dpi) + 6 PDF (vector) figures to `notebooks/figures/` for the written report

---

## 🛠️ Tech Stack

- **Backend** — Python 3.9+, Flask, pandas, numpy
- **Frontend** — HTML, dark-theme CSS (vanilla, no framework), vanilla JavaScript, Plotly.js
- **Notebook** — matplotlib, seaborn, jupyter
- **Single source of truth** — `analysis.py` returns raw data dicts that both the live dashboard (Plotly) and the static notebook (matplotlib) consume; numbers can never drift between them

---

## 📂 Structure

```
reelvana/
├── app.py                  # Flask routes + page rendering
├── data_loader.py          # CSV → DataFrame, poster lookup, weighted_score column
├── analysis.py             # 9 chart-data functions + KPI summary (raw dicts only)
├── recommender.py          # V2 stub — see PROJECT_STATUS.md
├── config.py               # Path constants, pagination defaults
├── requirements.txt
│
├── data/
│   ├── processed/          # movies_final_clean.csv, ratings_clean.csv (read-only)
│   └── raw/                # original TMDB + MovieLens dumps (git-ignored, ~700MB)
│
├── templates/              # movie_list, movie_detail, analysis, recommender
├── static/
│   ├── style.css           # one stylesheet
│   ├── script.js           # one frontend module (search, infinite scroll, filters)
│   └── posters/            # 8,473 .jpg images keyed by IMDB id (git-ignored)
│
├── notebooks/
│   ├── eda.ipynb           # Q1+Q2 EDA in matplotlib
│   ├── plot_style.py       # matplotlib theme + 3 palettes
│   └── figures/            # 6 PNG + 6 PDF — paste-ready for report/PPT
│
├── docs/
│   ├── assignment/         # GroupProject26.pdf
│   ├── analysis/           # team's MATLAB Q1/Q2 baseline (q1.m, q2.m, PDFs)
│   ├── ui_reference/       # SDS UI mockups
│   └── SoftwareDesignSpecification_1.3(4).docx
│
├── PROJECT_STATUS.md       # ongoing project log
├── CLAUDE.md               # Claude Code project guide
└── README.md               # this file
```

---

## 🚀 Run Locally

```bash
# 1. Clone
git clone https://github.com/<your-username>/reelvana.git
cd reelvana

# 2. Create virtual env
python -m venv venv
# Windows:  venv\Scripts\activate
# macOS:    source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python app.py
```

Open <http://localhost:5000>. Startup takes ~3-5 seconds (one-time CSV load + poster lookup build).

### Re-running the EDA notebook

```bash
cd notebooks
python -m jupyter nbconvert --to notebook --execute eda.ipynb --output eda.ipynb
```

Regenerates 12 files in `notebooks/figures/` from the same `analysis.py` functions that drive the live dashboard.

---

## 📊 Datasets

| File | Rows | Used as |
|---|---|---|
| `data/processed/movies_final_clean.csv` | 22,720 raw → **22,620 usable** | Primary source for everything. 100 rows dropped during cleaning (CSV column-shift corruption). |
| `data/processed/ratings_clean.csv` | 40,009 | Held in reserve — V2 recommender will use it via the `links.csv` movieId↔tmdbId bridge |
| `data/raw/links.csv` | 45,624 with non-null tmdbId | Bridge between TMDB id and IMDB id (used for poster lookup) |

See `PROJECT_STATUS.md` for the full data-cleaning audit (what was dropped and why).

---

## 📈 Routes

| Route | Page | Notes |
|---|---|---|
| `GET /` | Movie list | Search + filter + sort + infinite scroll |
| `GET /movie/<id>` | Movie detail | Jinja-rendered |
| `GET /analysis` | Analytics dashboard | 9 Plotly charts in 3 groups |
| `GET /recommender` | Placeholder | V2 — not implemented |
| `GET /api/genres` | JSON | 20 canonical TMDB genres |
| `GET /api/movies` | JSON | `?genre=…&sort=normal\|popular\|rate\|date&q=…&page=…&per_page=…` (max 100/page) |
| `GET /api/movies/<id>` | JSON | Full detail (heavy fields) |
| `GET /api/charts/<name>` | JSON | One of 9 chart data dicts (raw, no Plotly config) |
| `GET /api/kpis` | JSON | Dashboard KPI summary |

---

## 🗺️ V2 Roadmap

- **Recommender engine** — TF-IDF on `overview + genres_parsed + keywords_parsed`, cosine similarity, in-memory at startup. The placeholder route + `recommender.py` stub are already wired.
- **User auth + rating history** — currently anonymous; V2 binds ratings to accounts via the existing `ratings_clean.csv` users
- **Frontend redesign** — V1 dashboard prioritizes data correctness over polish; V2 will revamp visual hierarchy

---

## 👥 Team

| Name | Student ID |
|---|---|
| CHEN Fengyuan | 2430026009 |
| CHEN Yixuan | 2430036019 |
| CHEN Zheyu | 2430026021 |
| YU Chengzhu | 2330026199 |
| ZHI Xiwen | 2330026231 |

---

## 📄 Documentation

- [Project Status](PROJECT_STATUS.md) — data-cleaning audit, file map, completion log
- [Software Design Specification](docs/SoftwareDesignSpecification_1.3(4).docx) — formal SDS doc
- [Claude Code Guide](CLAUDE.md) — coding conventions for AI-assisted edits
- [Course Brief](docs/assignment/GroupProject26.pdf) — original assignment

---

Created for CST3104 at UIC, 2025-2026 Spring Semester.
