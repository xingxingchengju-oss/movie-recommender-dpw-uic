(function () {
  const ALL = "All";
  let currentGenre = ALL;
  let currentSort = "normal";
  let currentPage = 1;
  let totalPages = 1;
  let isLoading = false;
  let allGenres = [];

  const genreContainer = document.getElementById("genre-filters");
  const gridContainer = document.getElementById("movie-grid");
  const sortWidget = document.getElementById("sort-select");
  const movieCount = document.getElementById("movie-count");

  if (!genreContainer || !gridContainer) return;

  let sentinel = null;
  let scrollObserver = null;

  function getPosterGradient(id) {
    const hue1 = (id * 137.508) % 360;
    const hue2 = (hue1 + 40) % 360;
    const hue3 = (hue1 + 80) % 360;
    const sat = 55 + (id % 3) * 10;
    const l1 = 18 + (id % 4) * 4;
    const l2 = 12 + (id % 3) * 3;
    return `radial-gradient(ellipse at 30% 20%, hsl(${hue1},${sat}%,${l1 + 8}%) 0%, hsl(${hue2},${sat - 10}%,${l1}%) 45%, hsl(${hue3},${sat - 20}%,${l2}%) 100%)`;
  }

  function observeCards(cards) {
    if (!("IntersectionObserver" in window)) {
      cards.forEach((c) => c.classList.add("is-visible"));
      return;
    }
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
  }

  function renderGenreTags() {
    const tags = [ALL, ...allGenres];
    genreContainer.innerHTML = tags
      .map(
        (g) =>
          `<button class="genre-tag${g === currentGenre ? " active" : ""}" data-genre="${g}">${g}</button>`
      )
      .join("");
  }

  function cardHTML(m, indexOffset) {
    const poster = m.poster_url
      ? `<div class="movie-poster" style="background-image:url('${m.poster_url}');background-size:cover;background-position:center"></div>`
      : `<div class="movie-poster" style="background:${getPosterGradient(m.id)}">
           <i data-lucide="film" class="poster-icon"></i>
         </div>`;
    const rating = m.vote_average != null ? m.vote_average.toFixed(1) : "—";
    const year = m.release_year != null ? m.release_year : "—";
    return `
      <a href="/movie/${m.id}" class="movie-card" data-id="${m.id}" style="animation-delay:${(indexOffset % 24) * 0.04}s">
        ${poster}
        <div class="movie-info">
          <div class="movie-title">${m.title}</div>
          <div class="movie-meta">
            <span class="movie-year">${year}</span>
            <span class="movie-rating">
              <svg viewBox="0 0 24 24" fill="#F5C518" stroke="none"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14l-5-4.87 6.91-1.01z"/></svg>
              ${rating}
            </span>
          </div>
        </div>
      </a>`;
  }

  function fetchMovies(reset) {
    if (isLoading) return;
    if (!reset && currentPage > totalPages) return;
    isLoading = true;

    const params = new URLSearchParams({
      page: reset ? 1 : currentPage,
      per_page: 24,
      sort: currentSort,
    });
    if (currentGenre !== ALL) params.set("genre", currentGenre);

    return fetch(`/api/movies?${params.toString()}`)
      .then((r) => r.json())
      .then((data) => {
        totalPages = data.total_pages;
        currentPage = data.page;

        if (reset) {
          gridContainer.innerHTML = "";
          if (movieCount) {
            movieCount.textContent = `${data.total.toLocaleString()} ${data.total === 1 ? "movie" : "movies"}`;
          }
        }

        if (reset && data.total === 0) {
          gridContainer.innerHTML = `
            <div class="empty-state">
              <i data-lucide="film"></i>
              <p>No movies found.</p>
            </div>`;
          lucide.createIcons();
          isLoading = false;
          return;
        }

        const startIndex = gridContainer.children.length;
        const html = data.movies.map((m, i) => cardHTML(m, startIndex + i)).join("");
        gridContainer.insertAdjacentHTML("beforeend", html);

        const newCards = Array.from(gridContainer.querySelectorAll(".movie-card")).slice(startIndex);
        observeCards(newCards);
        lucide.createIcons();

        currentPage += 1;
        attachScrollSentinel();
        isLoading = false;
      })
      .catch((err) => {
        console.error("Failed to fetch movies:", err);
        isLoading = false;
      });
  }

  function attachScrollSentinel() {
    if (scrollObserver) scrollObserver.disconnect();
    if (sentinel && sentinel.parentNode) sentinel.parentNode.removeChild(sentinel);
    if (currentPage > totalPages) return;

    sentinel = document.createElement("div");
    sentinel.className = "scroll-sentinel";
    sentinel.style.height = "1px";
    gridContainer.parentNode.insertBefore(sentinel, gridContainer.nextSibling);

    scrollObserver = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) fetchMovies(false);
      },
      { rootMargin: "400px" }
    );
    scrollObserver.observe(sentinel);
  }

  function reload() {
    currentPage = 1;
    totalPages = 1;
    fetchMovies(true);
  }

  // Sort widget
  if (sortWidget) {
    const trigger = sortWidget.querySelector(".custom-select-trigger");
    const valueEl = sortWidget.querySelector(".custom-select-value");
    const options = sortWidget.querySelectorAll(".custom-select-option");

    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      const isOpen = sortWidget.classList.toggle("open");
      trigger.setAttribute("aria-expanded", isOpen);
    });

    options.forEach((opt) => {
      opt.addEventListener("click", () => {
        currentSort = opt.dataset.value;
        valueEl.textContent = opt.textContent;
        options.forEach((o) => o.classList.remove("active"));
        opt.classList.add("active");
        sortWidget.classList.remove("open");
        trigger.setAttribute("aria-expanded", "false");
        reload();
      });
    });

    document.addEventListener("click", () => {
      sortWidget.classList.remove("open");
      trigger.setAttribute("aria-expanded", "false");
    });
  }

  // Genre filter clicks
  genreContainer.addEventListener("click", (e) => {
    const tag = e.target.closest(".genre-tag");
    if (!tag) return;
    currentGenre = tag.dataset.genre;
    renderGenreTags();
    reload();
  });

  // Bootstrap: load genres then first page
  fetch("/api/genres")
    .then((r) => r.json())
    .then((genres) => {
      allGenres = genres;
      renderGenreTags();
      reload();
    })
    .catch((err) => {
      console.error("Failed to fetch genres:", err);
      reload();
    });
})();
