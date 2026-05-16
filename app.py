import re

import pandas as pd
from flask import Flask, abort, jsonify, render_template, request

import analysis
import config
from recommenders import hybrid
from recommenders import item_based as recommender
from recommenders import user_based as user_recommender
from recommenders.curated import CURATED_USERS
from data_loader import load_movies, movie_to_detail_dict, movie_to_list_dict

app = Flask(__name__)

print("[startup] Loading movies dataset...")
DF_MOVIES, GENRES = load_movies()
print(f"[startup] Loaded {len(DF_MOVIES)} movies, {len(GENRES)} unique genres, "
      f"{DF_MOVIES['poster_url'].notna().sum()} with posters.")

print("[startup] Building recommender index...")
recommender.build(DF_MOVIES)
_rec_status = recommender.get_status()
print(f"[startup] Recommender ready: {_rec_status['n_movies']} movies × "
      f"{_rec_status['n_features']} features")

print("[startup] Building user recommender (SVD)...")
_ratings_df = pd.read_csv(config.RATINGS_CSV)
_links_df = pd.read_csv(config.LINKS_CSV)
user_recommender.build(_ratings_df, _links_df, DF_MOVIES)
_user_rec_status = user_recommender.get_status()
print(f"[startup] User recommender ready: {_user_rec_status['n_users']} users × "
      f"{_user_rec_status['n_movies']} movies")


@app.route("/")
def page_movie_list():
    return render_template("movie_list.html", active_page="movies")


@app.route("/recommender")
def page_recommender():
    return render_template("recommender.html", active_page="recommender")


@app.route("/movie/<int:movie_id>")
def page_movie_detail(movie_id):
    rows = DF_MOVIES[DF_MOVIES["id"] == movie_id]
    if rows.empty:
        abort(404)
    movie = movie_to_detail_dict(rows.iloc[0])
    return render_template("movie_detail.html", movie=movie, active_page="movies")


@app.route("/analysis")
def page_analysis():
    return render_template(
        "analysis.html",
        kpis=analysis.kpi_summary(DF_MOVIES),
        active_page="analysis",
    )


@app.route("/api/kpis")
def api_kpis():
    return jsonify(analysis.kpi_summary(DF_MOVIES))


@app.route("/api/charts/<chart_name>")
def api_chart(chart_name):
    fn = analysis.CHART_FUNCTIONS.get(chart_name)
    if fn is None:
        return jsonify({"error": f"unknown chart: {chart_name}"}), 404
    return jsonify(fn(DF_MOVIES))


@app.route("/api/genres")
def api_genres():
    return jsonify(GENRES)


@app.route("/api/movies/<int:movie_id>")
def api_movie_detail(movie_id):
    rows = DF_MOVIES[DF_MOVIES["id"] == movie_id]
    if rows.empty:
        return jsonify({"error": "movie not found"}), 404
    return jsonify(movie_to_detail_dict(rows.iloc[0]))


@app.route("/api/recommend/<int:movie_id>")
def api_recommend(movie_id):
    try:
        n = max(1, min(int(request.args.get("n", 10)), 50))
    except ValueError:
        n = 10
    recs = recommender.get_recommendations(movie_id, n)
    if not recs:
        return jsonify({
            "error": "no recommendations available",
            "hint": "movie may be non-English or not in the index",
            "recommendations": [],
        }), 404
    return jsonify({"recommendations": recs})


@app.route("/api/users")
def api_users():
    return jsonify({"users": CURATED_USERS})


@app.route("/api/recommend/user/<int:user_id>")
def api_recommend_user(user_id):
    try:
        n = max(1, min(int(request.args.get("n", 20)), 50))
    except ValueError:
        n = 20
    recs = user_recommender.get_user_recommendations(user_id, n)
    if not recs:
        return jsonify({
            "error": "no recommendations available",
            "hint": "user not in trained SVD index",
            "recommendations": [],
        }), 404
    return jsonify({"recommendations": recs})


@app.route("/api/recommend/build", methods=["POST"])
def api_recommend_build():
    """V2C: hybrid recommendation from a list of liked movies.

    Body: {movie_ids: int[], alpha?: float in [0,1], n?: int}
    alpha=0 → pure content (V1 TF-IDF aggregation).
    alpha=1 → pure collaborative filtering (V2A SVD fold-in).
    """
    payload = request.get_json(silent=True) or {}
    raw_ids = payload.get("movie_ids", [])

    try:
        alpha = float(payload.get("alpha", 0.5))
    except (TypeError, ValueError):
        alpha = 0.5
    alpha = max(0.0, min(1.0, alpha))

    try:
        n = max(1, min(int(payload.get("n", 20)), 50))
    except (TypeError, ValueError):
        n = 20

    if not isinstance(raw_ids, list) or not raw_ids:
        return jsonify({
            "error": "movie_ids must be a non-empty list",
            "recommendations": [],
        }), 400
    try:
        movie_ids = [int(x) for x in raw_ids]
    except (TypeError, ValueError):
        return jsonify({
            "error": "movie_ids must contain integers",
            "recommendations": [],
        }), 400

    try:
        result = hybrid.recommend(movie_ids, n=n, alpha=alpha)
    except ValueError as exc:
        return jsonify({
            "error": "no hybrid input",
            "hint": str(exc),
            "recommendations": [],
        }), 422

    return jsonify(result)


@app.route("/api/predict_rating/<int:user_id>/<int:movie_id>")
def api_predict_rating(user_id, movie_id):
    rating = user_recommender.predict_rating(user_id, movie_id)
    if rating is None:
        if not user_recommender.has_user(user_id):
            hint = "user not in trained SVD index"
        else:
            hint = "movie not in trained SVD index (no MovieLens ratings)"
        return jsonify({
            "predicted_rating": None,
            "error": "no prediction available",
            "hint": hint,
        }), 404
    return jsonify({"predicted_rating": rating})


@app.route("/api/movies")
def api_movies():
    genre = request.args.get("genre", "").strip()
    sort = request.args.get("sort", "normal").strip()
    q = request.args.get("q", "").strip()

    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    try:
        per_page = int(request.args.get("per_page", config.PER_PAGE_DEFAULT))
    except ValueError:
        per_page = config.PER_PAGE_DEFAULT
    per_page = max(1, min(per_page, config.PER_PAGE_MAX))

    df = DF_MOVIES
    if genre and genre.lower() != "all":
        mask = df["genres_list"].apply(lambda lst: genre in lst)
        df = df[mask]
    if q:
        # Forgiving title match: normalize query the same way as title_norm
        # (strip non-alphanumerics + lowercase) so "ironman" finds "Iron Man",
        # "lordoftherings" finds "The Lord of the Rings", etc. Empty after
        # normalization (e.g. q="!!!") falls through and returns everything.
        norm_q = re.sub(r"[^a-z0-9]", "", q.lower())
        if norm_q:
            df = df[df["title_norm"].str.contains(norm_q, case=False, na=False, regex=False)]

    if sort == "popular":
        df = df.sort_values("weighted_score", ascending=False, na_position="last")
    elif sort == "rate":
        df = df.sort_values("vote_average", ascending=False, na_position="last")
    elif sort == "date":
        df = df.sort_values("release_year", ascending=False, na_position="last")

    total = len(df)
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    end = start + per_page
    page_df = df.iloc[start:end]

    movies = [movie_to_list_dict(row) for _, row in page_df.iterrows()]

    return jsonify({
        "movies": movies,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    })


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
