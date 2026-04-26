# 🎬 CineMatch

> Movie analytics & recommendation web app powered by TMDB + MovieLens.

Group project for **CST3104 Software Development Workshop II** at United International College (Spring 2025-2026).

---

## ✨ Features

- 🎬 **Movie List** — Browse movies with genre filters and search
- 📊 **Data Analysis** — Visualizations of trends, genres, and ratings
- ✨ **Recommender** — Personalized recommendations using TF-IDF + cosine similarity
- 🎨 **Custom UI** — Dark-themed interface with HTML, CSS, and vanilla JS

---

## 🛠️ Tech Stack

- **Backend:** Python 3.9+, Flask
- **Frontend:** HTML, CSS, Vanilla JavaScript, Plotly.js
- **Data:** pandas, scikit-learn

---

## 📂 Structure

```
cinematch/
├── app.py              # Flask app & all routes
├── recommender.py      # TF-IDF recommendation logic
├── analysis.py         # Chart data functions
├── requirements.txt
├── data/               # movies_clean.csv, ratings_clean.csv
├── templates/          # HTML pages
├── static/             # CSS, JS, images
├── notebooks/          # EDA notebooks
└── docs/               # SDS, report, presentation
```

---

## 🚀 Run Locally

```bash
# 1. Clone
git clone https://github.com/<your-username>/cinematch.git
cd cinematch

# 2. Create virtual env
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python app.py
```

Open http://localhost:5000 in your browser.

---

## 📊 Datasets

| File | Rows | Description |
|---|---|---|
| `data/movies_clean.csv` | 22,796 | Movie metadata |
| `data/ratings_clean.csv` | 40,008 | User ratings |

Pre-cleaned. Source: TMDB + MovieLens. Coverage: movies released on or before July 2017.

---

## 📈 Pages

| Route | Description |
|---|---|
| `/` | Movie list |
| `/movie/<id>` | Movie detail |
| `/analysis` | Data analysis dashboard |
| `/recommender` | Recommendation form |

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

- [System Design Specification (SDS) v1.3](docs/sds_v1.3.pdf)
- [Claude Code Guide](CLAUDE.md)

---

Created for CST3104 at UIC, 2025-2026 Spring Semester.
