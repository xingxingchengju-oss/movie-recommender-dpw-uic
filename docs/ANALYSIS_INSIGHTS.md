# Reelvana — EDA Insights

Nine charts across three thematic sections answer the question *"what does the TMDB + MovieLens corpus (≤ July 2017, 22,620 cleaned films) actually look like?"* Each chart-derived insight below is reproducible from the live dashboard at `/analysis` and exported as static figures under `notebooks/figures/`.

---

## Section 1 — Production & Genre Trends

> *How film production exploded across 14 decades — and which genres rose with it.*

### 1.1 Production trend by decade
**The 2010s alone produced 7,360 films — about 1.7× the entire 1870–1970 century combined.** Film output curves exponentially across the 20th century with three visible inflection points: the silent-era boom (1910s–1920s), the sound/studio era (1930s–1950s), and the digital-distribution surge (2000s–2010s).

### 1.2 Genre evolution (per-decade share)
**Drama has led every decade since 1920.** Among the eight dominant genres, **Documentary's share grew 66%** from the 2000s (4.7%) to the 2010s (7.8%) — a reflection of cheaper production and streaming-led demand for non-fiction.

### 1.3 Genre heatmap (decade × genre)
**Drama's dominance peaked in the 1990s at ~30%** of all releases. Comedy and Documentary have been chipping away at that lead in the modern era. (Pre-1900 decades only have 1–3 films each, so any "100%" cell there is a small-sample artifact and was annotated.)

---

## Section 2 — Financial Patterns

> *Money in vs. money out — what disclosed-financial films tell us about the economics of cinema.*

### 2.1 Budget vs revenue (log-log, regression)
**The median film returns $2.12 per $1 of budget.** The log-log elasticity is **0.86**, meaning revenue grows slightly *slower* than budget on average — there are diminishing returns at the high end (you can spend more, but you can't reliably extract a proportional revenue lift past a ceiling).

### 2.2 ROI distribution by genre
**Among films that at least broke even, Horror leads at 3.55× median return,** edging Animation (3.37×) and Drama (3.18×). Low-budget, high-leverage genres extract the most multiplier — the same reason horror dominates indie production economics in the real world.

### 2.3 Financial correlation matrix
**Revenue and Profit move in lockstep (r = 0.98)**, which is expected — but **ROI is uncorrelated with budget, revenue, or popularity**. Small films can still win huge; budget is *not* a predictor of return-on-investment.

---

## Section 3 — Audience Reception

> *How TMDB users rate films across history, genre, and the long tail of taste.*

### 3.1 Rating distribution
**Ratings cluster sharply around 6.0–6.5 (peak bin: 4,556 films)** with a long left tail toward low scores. TMDB users rate generously — they only go low when they really mean it.

### 3.2 Rating trend by decade
**Modern films hover steadily around 6.0–6.3, while older films skew higher (1920s peak: 7.03 mean rating).** This is **survival bias**: the only pre-1950 films that get rated today are the ones canonical enough to have survived. The flat modern trend is the more honest signal of "what the average new release scores."

### 3.3 Rating by genre
**Documentary tops at 7.10 median rating; Horror sits last at 5.40.** Compared with Section 2.2 — horror is the *most profitable* genre but the *least loved* by rating; documentary inverts that. Critical reception and commercial leverage are nearly orthogonal.

---

## Cross-section synthesis

Reading the three sections together produces one defensible meta-insight:

> **Production volume, financial leverage, and audience reception each tell a different story about the same film.** A film that wins on volume of competition (the 2010s, drama-heavy) does not automatically win on margin (horror leads), and neither volume nor margin predicts whether the audience will love it (documentary tops on rating). These three axes are the foundation of the recommendation engines built on top of this data: V1 (TF-IDF) leverages genre/keywords, V2A (SVD) leverages user-rating patterns, and V2C (hybrid) blends both.

---

## Reproducibility

| Asset                                  | How to regenerate                                                  |
|----------------------------------------|--------------------------------------------------------------------|
| Live dashboard                         | `python app.py` → `http://127.0.0.1:5000/analysis`                 |
| All nine chart payloads (JSON)         | `GET /api/charts/<chart_name>` — see `analysis.CHART_FUNCTIONS`    |
| Static PNG + PDF exports for the slides| `jupyter nbconvert --execute notebooks/eda.ipynb` (writes to `notebooks/figures/`) |
| KPI summary                            | `GET /api/kpis`                                                    |
