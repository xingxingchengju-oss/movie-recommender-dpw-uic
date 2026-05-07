(function () {
  const ALL = "All";
  let currentGenre = ALL;
  let currentSort = "normal";
  let currentQuery = "";
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
    if (currentQuery) params.set("q", currentQuery);

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
        // Use the full visible label (e.g. "Popular") not just the option's
        // shorter label — copy from the option text to keep them in sync.
        valueEl.textContent = opt.textContent.trim();
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

  // ── Search with autocomplete dropdown ─────────────────────────────────
  const searchWrap     = document.getElementById("search-wrap");
  const searchInput    = document.getElementById("search-input");
  const searchDropdown = document.getElementById("search-dropdown");
  const searchSpinner  = document.getElementById("search-spinner");
  const searchClear    = document.getElementById("search-clear");

  if (searchInput && searchDropdown) {
    let debounceTimer = null;
    let currentSearchAbort = null;
    const MIN_CHARS = 2;
    const DEBOUNCE_MS = 250;

    function escapeHTML(s) {
      return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }

    function highlightMatch(title, query) {
      if (!query) return escapeHTML(title);
      const safeTitle = escapeHTML(title);
      const safeQuery = escapeHTML(query).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return safeTitle.replace(new RegExp(`(${safeQuery})`, "ig"), "<mark>$1</mark>");
    }

    function suggestionRow(m, query) {
      const poster = m.poster_url
        ? `<div class="sug-poster" style="background-image:url('${m.poster_url}');background-size:cover;background-position:center"></div>`
        : `<div class="sug-poster" style="background:${getPosterGradient(m.id)}"></div>`;
      const year = m.release_year != null ? m.release_year : "—";
      const rating = m.vote_average != null ? m.vote_average.toFixed(1) : "—";
      return `
        <a class="sug-row" href="/movie/${m.id}" role="option">
          ${poster}
          <div class="sug-meta">
            <div class="sug-title">${highlightMatch(m.title, query)}</div>
            <div class="sug-sub">${year}</div>
          </div>
          <div class="sug-rating">★ ${rating}</div>
        </a>`;
    }

    function renderDropdown(state, payload) {
      searchDropdown.classList.add("open");
      if (state === "loading") {
        searchDropdown.innerHTML = `<div class="sug-status">Searching…</div>`;
      } else if (state === "empty") {
        searchDropdown.innerHTML =
          `<div class="sug-status">No films match <strong>${escapeHTML(payload)}</strong>.</div>`;
      } else if (state === "results") {
        const { movies, total, query } = payload;
        const rows = movies.map((m) => suggestionRow(m, query)).join("");
        const more = total > movies.length
          ? `<button class="sug-viewall" type="button" data-query="${escapeHTML(query)}">View all ${total.toLocaleString()} results →</button>`
          : "";
        searchDropdown.innerHTML = rows + more;
      }
    }

    function closeDropdown() {
      searchDropdown.classList.remove("open");
      searchDropdown.innerHTML = "";
    }

    function applySearchToGrid(query) {
      currentQuery = query;
      reload();
      closeDropdown();
    }

    async function searchMovies(query) {
      if (currentSearchAbort) currentSearchAbort.abort();
      currentSearchAbort = new AbortController();
      searchSpinner.classList.add("active");
      try {
        const r = await fetch(
          `/api/movies?q=${encodeURIComponent(query)}&per_page=5`,
          { signal: currentSearchAbort.signal }
        );
        const data = await r.json();
        if (data.total === 0) {
          renderDropdown("empty", query);
        } else {
          renderDropdown("results", { movies: data.movies, total: data.total, query });
        }
      } catch (e) {
        if (e.name !== "AbortError") {
          console.error("Search failed:", e);
          searchDropdown.innerHTML = `<div class="sug-status">Search error.</div>`;
        }
      } finally {
        searchSpinner.classList.remove("active");
      }
    }

    searchInput.addEventListener("input", (e) => {
      const q = e.target.value.trim();
      searchClear.classList.toggle("visible", q.length > 0);
      clearTimeout(debounceTimer);
      if (q.length < MIN_CHARS) {
        if (currentSearchAbort) currentSearchAbort.abort();
        searchSpinner.classList.remove("active");
        closeDropdown();
        // If user wiped the query, reset the grid to unfiltered
        if (q.length === 0 && currentQuery) {
          currentQuery = "";
          reload();
        }
        return;
      }
      renderDropdown("loading");
      debounceTimer = setTimeout(() => searchMovies(q), DEBOUNCE_MS);
    });

    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closeDropdown();
        searchInput.blur();
      } else if (e.key === "Enter") {
        const q = searchInput.value.trim();
        if (q.length >= MIN_CHARS) applySearchToGrid(q);
      }
    });

    searchInput.addEventListener("focus", () => {
      const q = searchInput.value.trim();
      if (q.length >= MIN_CHARS && searchDropdown.children.length) {
        searchDropdown.classList.add("open");
      }
    });

    searchClear.addEventListener("click", () => {
      searchInput.value = "";
      searchClear.classList.remove("visible");
      closeDropdown();
      if (currentQuery) {
        currentQuery = "";
        reload();
      }
      searchInput.focus();
    });

    searchDropdown.addEventListener("click", (e) => {
      const viewAll = e.target.closest(".sug-viewall");
      if (viewAll) {
        e.preventDefault();
        applySearchToGrid(viewAll.dataset.query);
      }
      // Suggestion rows are <a> — let default navigation happen
    });

    // Close dropdown when clicking outside the search wrap
    document.addEventListener("click", (e) => {
      if (!searchWrap.contains(e.target)) closeDropdown();
    });
  }

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
