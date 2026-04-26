(function () {
  let currentGenre = "All";
  let currentSort = "normal";

  const genreContainer = document.getElementById("genre-filters");
  const gridContainer  = document.getElementById("movie-grid");
  const sortSelect     = document.getElementById("sort-select");
  const movieCount     = document.getElementById("movie-count");

  if (!genreContainer || !gridContainer) return;

  function getPosterGradient(id) {
    const hue1 = (id * 137.508) % 360;
    const hue2 = (hue1 + 40) % 360;
    const hue3 = (hue1 + 80) % 360;
    const sat  = 55 + (id % 3) * 10;
    const l1   = 18 + (id % 4) * 4;
    const l2   = 12 + (id % 3) * 3;
    return `radial-gradient(ellipse at 30% 20%, hsl(${hue1},${sat}%,${l1 + 8}%) 0%, hsl(${hue2},${sat - 10}%,${l1}%) 45%, hsl(${hue3},${sat - 20}%,${l2}%) 100%)`;
  }

  function observeCards() {
    const cards = gridContainer.querySelectorAll(".movie-card");
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver(
        (entries) =>
          entries.forEach((e) => {
            if (e.isIntersecting) {
              e.target.classList.add("is-visible");
              io.unobserve(e.target);
            }
          }),
        { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
      );
      cards.forEach((c) => io.observe(c));
    } else {
      cards.forEach((c) => c.classList.add("is-visible"));
    }
  }

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

    if (movieCount) {
      movieCount.textContent = `${movies.length} ${movies.length === 1 ? "movie" : "movies"}`;
    }

    if (movies.length === 0) {
      gridContainer.innerHTML = `
        <div class="empty-state">
          <i data-lucide="film"></i>
          <p>No movies found for this genre.</p>
        </div>`;
      lucide.createIcons();
      return;
    }

    gridContainer.innerHTML = movies
      .map(
        (m, i) => `
      <div class="movie-card" data-id="${m.id}" style="animation-delay:${i * 0.05}s">
        <div class="movie-poster" style="background:${getPosterGradient(m.id)}">
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
    observeCards();
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
    window.location.href = `movie_detail.html?id=${card.dataset.id}`;
  });

  renderGenreTags();
  renderMovies();
})();
