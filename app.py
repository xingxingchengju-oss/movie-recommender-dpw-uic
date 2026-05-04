from flask import Flask, abort, jsonify, render_template, request

import analysis
import config
from data_loader import load_movies, movie_to_detail_dict, movie_to_list_dict

app = Flask(__name__)

print("[startup] Loading movies dataset...")
DF_MOVIES, GENRES = load_movies()
print(f"[startup] Loaded {len(DF_MOVIES)} movies, {len(GENRES)} unique genres, "
      f"{DF_MOVIES['poster_url'].notna().sum()} with posters.")


@app.route("/")
def page_movie_list():
    return render_template("movie_list.html", active_page="movies")


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
        df = df[df["title"].str.contains(q, case=False, na=False)]

    if sort == "rate":
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
