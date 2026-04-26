(function () {
  let currentGenre = "All";
  let currentSort = "normal";

  const genreContainer = document.getElementById("genre-filters");
  const gridContainer = document.getElementById("movie-grid");
  const sortSelect = document.getElementById("sort-select");

  if (!genreContainer || !gridContainer) return;

  function renderGenreTags() {
    genreContainer.innerHTML = ALL_GENRES.map(
      (g) =>
        `<button class="genre-tag${g === currentGenre ? " active" : ""}" data-genre="${g}">${g}</button>`
    ).join("");
  }

  function getFilteredMovies() {
    let movies =
      currentGenre === "All"
        ? [...MOCK_MOVIES]
        : MOCK_MOVIES.filter((m) => m.genres.includes(currentGenre));

    if (currentSort === "rate") {
      movies.sort((a, b) => b.vote_average - a.vote_average);
    } else if (currentSort === "date") {
      movies.sort((a, b) => b.release_year - a.release_year);
    }
    return movies;
  }

  function renderMovies() {
    const movies = getFilteredMovies();
    if (movies.length === 0) {
      gridContainer.innerHTML = `
        <div class="empty-state" style="grid-column:1/-1">
          <i data-lucide="film" style="width:48px;height:48px;opacity:.4"></i>
          <p>No movies found for this genre.</p>
        </div>`;
      lucide.createIcons();
      return;
    }

    gridContainer.innerHTML = movies
      .map(
        (m) => `
      <div class="movie-card" data-id="${m.id}">
        <div class="movie-poster">
          <i data-lucide="film" class="poster-icon"></i>
        </div>
        <div class="movie-info">
          <div class="movie-title">${m.title}</div>
          <div class="movie-meta">
            <span class="movie-year">${m.release_year}</span>
            <span class="movie-rating">
              <svg viewBox="0 0 24 24" fill="#F5C518" stroke="none"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14l-5-4.87 6.91-1.01z"/></svg>
              ${m.vote_average.toFixed(1)}
            </span>
          </div>
        </div>
      </div>`
      )
      .join("");

    lucide.createIcons();
  }

  genreContainer.addEventListener("click", (e) => {
    const tag = e.target.closest(".genre-tag");
    if (!tag) return;
    currentGenre = tag.dataset.genre;
    renderGenreTags();
    renderMovies();
  });

  sortSelect.addEventListener("change", (e) => {
    currentSort = e.target.value;
    renderMovies();
  });

  gridContainer.addEventListener("click", (e) => {
    const card = e.target.closest(".movie-card");
    if (!card) return;
    const movieId = card.dataset.id;
    window.location.href = `movie_detail.html?id=${movieId}`;
  });

  renderGenreTags();
  renderMovies();
})();