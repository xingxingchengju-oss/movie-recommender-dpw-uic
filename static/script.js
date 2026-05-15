// ── Shared helpers (used by movie list, movie detail recs, recommender page) ──
function getPosterGradient(id) {
  const hue1 = (id * 137.508) % 360;
  const hue2 = (hue1 + 40) % 360;
  const hue3 = (hue1 + 80) % 360;
  const sat = 55 + (id % 3) * 10;
  const l1 = 18 + (id % 4) * 4;
  const l2 = 12 + (id % 3) * 3;
  return `radial-gradient(ellipse at 30% 20%, hsl(${hue1},${sat}%,${l1 + 8}%) 0%, hsl(${hue2},${sat - 10}%,${l1}%) 45%, hsl(${hue3},${sat - 20}%,${l2}%) 100%)`;
}

function escapeHTML(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
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

function renderMovieCard(m, indexOffset) {
  const poster = m.poster_url
    ? `<div class="movie-poster" style="background-image:url('${m.poster_url}');background-size:cover;background-position:center"></div>`
    : `<div class="movie-poster" style="background:${getPosterGradient(m.id)}">
         <i data-lucide="film" class="poster-icon"></i>
       </div>`;
  const rating = m.vote_average != null ? m.vote_average.toFixed(1) : "—";
  const year = m.release_year != null ? m.release_year : "—";
  const delay = ((indexOffset || 0) % 24) * 0.04;
  return `
    <a href="/movie/${m.id}" class="movie-card" data-id="${m.id}" style="animation-delay:${delay}s">
      ${poster}
      <div class="movie-info">
        <div class="movie-title">${escapeHTML(m.title)}</div>
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

  function renderGenreTags() {
    const tags = [ALL, ...allGenres];
    genreContainer.innerHTML = tags
      .map(
        (g) =>
          `<button class="genre-tag${g === currentGenre ? " active" : ""}" data-genre="${g}">${g}</button>`
      )
      .join("");
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
        const html = data.movies.map((m, i) => renderMovieCard(m, startIndex + i)).join("");
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

// ── Movie detail: "More Like This" grid ────────────────────────────────
(function () {
  const grid = document.getElementById("similar-grid");
  if (!grid) return;

  const movieId = grid.dataset.movieId;
  fetch(`/api/recommend/${movieId}?n=12`)
    .then((r) => (r.ok ? r.json() : { recommendations: [] }))
    .then((data) => {
      const recs = data.recommendations || [];
      if (recs.length === 0) {
        grid.innerHTML = `<p class="empty-note">No similar films available for this title.</p>`;
        return;
      }
      grid.innerHTML = recs.map((m, i) => renderMovieCard(m, i)).join("");
      observeCards(Array.from(grid.querySelectorAll(".movie-card")));
      if (window.lucide) lucide.createIcons();
    })
    .catch((err) => {
      console.error("Failed to load recommendations:", err);
      grid.innerHTML = `<p class="empty-note">Could not load recommendations.</p>`;
    });
})();

// ── Recommender page: search → pick movie → show recommendations ───────
(function () {
  const searchInput = document.getElementById("rec-search");
  const suggestionsBox = document.getElementById("rec-suggestions");
  const selectedBox = document.getElementById("rec-selected");
  const resultsGrid = document.getElementById("rec-results");
  if (!searchInput || !suggestionsBox || !resultsGrid) return;

  const MIN_CHARS = 2;
  const DEBOUNCE_MS = 200;
  let debounceTimer = null;
  let currentAbort = null;

  function closeSuggestions() {
    suggestionsBox.classList.remove("open");
    suggestionsBox.innerHTML = "";
  }

  function renderSuggestions(movies, query) {
    if (!movies.length) {
      suggestionsBox.innerHTML = `<li class="rec-sug-empty">No films match <strong>${escapeHTML(query)}</strong>.</li>`;
      suggestionsBox.classList.add("open");
      return;
    }
    suggestionsBox.innerHTML = movies
      .map((m) => {
        const year = m.release_year != null ? m.release_year : "—";
        const rating = m.vote_average != null ? m.vote_average.toFixed(1) : "—";
        const poster = m.poster_url
          ? `<div class="rec-sug-poster" style="background-image:url('${m.poster_url}');background-size:cover;background-position:center"></div>`
          : `<div class="rec-sug-poster" style="background:${getPosterGradient(m.id)}"></div>`;
        return `
          <li class="rec-sug-row" data-id="${m.id}" data-title="${escapeHTML(m.title)}">
            ${poster}
            <div class="rec-sug-meta">
              <div class="rec-sug-title">${escapeHTML(m.title)}</div>
              <div class="rec-sug-sub">${year} · ★ ${rating}</div>
            </div>
          </li>`;
      })
      .join("");
    suggestionsBox.classList.add("open");
  }

  async function searchMovies(query) {
    if (currentAbort) currentAbort.abort();
    currentAbort = new AbortController();
    try {
      const r = await fetch(
        `/api/movies?q=${encodeURIComponent(query)}&per_page=8`,
        { signal: currentAbort.signal }
      );
      const data = await r.json();
      renderSuggestions(data.movies || [], query);
    } catch (e) {
      if (e.name !== "AbortError") console.error("Recommender search failed:", e);
    }
  }

  function selectMovie(id, title) {
    closeSuggestions();
    searchInput.value = title;
    selectedBox.innerHTML = `
      <div class="rec-selected-card">
        <span class="rec-selected-label">Recommendations based on</span>
        <span class="rec-selected-title">${escapeHTML(title)}</span>
      </div>`;
    resultsGrid.innerHTML = `<p class="empty-note">Loading similar films…</p>`;

    fetch(`/api/recommend/${id}?n=20`)
      .then((r) => (r.ok ? r.json() : { recommendations: [] }))
      .then((data) => {
        const recs = data.recommendations || [];
        if (recs.length === 0) {
          resultsGrid.innerHTML = `<p class="empty-note">No recommendations available for this title.</p>`;
          return;
        }
        resultsGrid.innerHTML = recs.map((m, i) => renderMovieCard(m, i)).join("");
        observeCards(Array.from(resultsGrid.querySelectorAll(".movie-card")));
        if (window.lucide) lucide.createIcons();
      })
      .catch((err) => {
        console.error("Recommendation fetch failed:", err);
        resultsGrid.innerHTML = `<p class="empty-note">Could not load recommendations.</p>`;
      });
  }

  searchInput.addEventListener("input", (e) => {
    const q = e.target.value.trim();
    clearTimeout(debounceTimer);
    if (q.length < MIN_CHARS) {
      closeSuggestions();
      return;
    }
    debounceTimer = setTimeout(() => searchMovies(q), DEBOUNCE_MS);
  });

  suggestionsBox.addEventListener("click", (e) => {
    const row = e.target.closest(".rec-sug-row");
    if (!row) return;
    selectMovie(row.dataset.id, row.dataset.title);
  });

  document.addEventListener("click", (e) => {
    if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
      closeSuggestions();
    }
  });

  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeSuggestions();
  });
})();

// ── Recommender page: tab switching ────────────────────────────────────
(function () {
  const tabs = document.querySelectorAll(".rec-tab");
  const panels = document.querySelectorAll(".rec-tab-panel");
  if (!tabs.length) return;

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      tabs.forEach((t) => {
        const active = t.dataset.tab === target;
        t.classList.toggle("active", active);
        t.setAttribute("aria-selected", active ? "true" : "false");
      });
      panels.forEach((p) => {
        const active = p.id === `tab-${target}`;
        p.classList.toggle("active", active);
        p.hidden = !active;
      });
    });
  });
})();

// ── Recommender page: For User tab — driven by sidebar + manual user lookup ─
(function () {
  const statusBox = document.getElementById("rec-user-status");
  const resultsGrid = document.getElementById("rec-user-results");
  const lookupInput = document.getElementById("rec-user-lookup-input");
  const lookupBtn = document.getElementById("rec-user-lookup-btn");
  const lookupErr = document.getElementById("rec-user-lookup-err");
  if (!statusBox || !resultsGrid || !lookupInput || !lookupBtn || !window.UserProfile) return;

  const GUEST_STATUS = "Pick a profile from the sidebar, or enter a MovieLens user ID.";
  let fetchSeq = 0;

  function showLookupError(msg) {
    lookupErr.textContent = msg;
    lookupErr.hidden = false;
  }

  function clearLookupError() {
    lookupErr.hidden = true;
    lookupErr.textContent = "";
  }

  function renderGuestState() {
    statusBox.textContent = GUEST_STATUS;
    resultsGrid.innerHTML = "";
  }

  function paintRecs(recs) {
    if (!recs.length) {
      resultsGrid.innerHTML = `<p class="empty-note">No recommendations available.</p>`;
      return;
    }
    resultsGrid.innerHTML = recs.map((m, i) => renderMovieCard(m, i)).join("");
    observeCards(Array.from(resultsGrid.querySelectorAll(".movie-card")));
    if (window.lucide) lucide.createIcons();
  }

  function loadForCuratedUser(user) {
    clearLookupError();
    statusBox.innerHTML = `
      Recommendations for <strong>${escapeHTML(user.label)}</strong>
      <span class="rec-user-status-meta">user #${user.id} · ${user.n_ratings} ratings · top genre ${escapeHTML(user.top_genre)}</span>
    `;
    resultsGrid.innerHTML = `<p class="empty-note">Loading personalized picks…</p>`;
    const seq = ++fetchSeq;
    fetch(`/api/recommend/user/${user.id}?n=20`)
      .then((r) => (r.ok ? r.json() : { recommendations: [] }))
      .then((data) => {
        if (seq !== fetchSeq) return;
        paintRecs(data.recommendations || []);
      })
      .catch((err) => {
        if (seq !== fetchSeq) return;
        console.error("User recs fetch failed:", err);
        resultsGrid.innerHTML = `<p class="empty-note">Could not load recommendations.</p>`;
      });
  }

  function loadForArbitraryId(userId) {
    statusBox.innerHTML = `
      Recommendations for <strong>MovieLens user #${userId}</strong>
      <span class="rec-user-status-meta">ad-hoc lookup · not saved to sidebar</span>
    `;
    resultsGrid.innerHTML = `<p class="empty-note">Loading personalized picks…</p>`;
    const seq = ++fetchSeq;
    fetch(`/api/recommend/user/${userId}?n=20`)
      .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
      .then(({ ok, data }) => {
        if (seq !== fetchSeq) return;
        if (!ok) {
          const hint = data.hint || "User ID not found.";
          showLookupError(hint);
          statusBox.textContent = GUEST_STATUS;
          resultsGrid.innerHTML = "";
          return;
        }
        clearLookupError();
        paintRecs(data.recommendations || []);
      })
      .catch((err) => {
        if (seq !== fetchSeq) return;
        console.error("Ad-hoc user recs fetch failed:", err);
        showLookupError("Could not load recommendations.");
      });
  }

  function submitLookup() {
    const raw = lookupInput.value.trim();
    if (!raw) {
      showLookupError("Please enter a user ID.");
      return;
    }
    if (!/^\d+$/.test(raw)) {
      showLookupError("Enter a numeric MovieLens user ID.");
      return;
    }
    clearLookupError();
    loadForArbitraryId(Number(raw));
  }

  lookupBtn.addEventListener("click", submitLookup);
  lookupInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      submitLookup();
    }
  });
  lookupInput.addEventListener("input", clearLookupError);

  // Sidebar profile changes always win — even if the user was viewing an
  // ad-hoc lookup, picking a sidebar profile snaps the tab back to that
  // profile's recommendations.
  window.addEventListener(window.UserProfile.EVENT, (e) => {
    const userId = e.detail.userId;
    clearLookupError();
    lookupInput.value = "";
    if (userId == null) {
      renderGuestState();
      return;
    }
    const user = window.UserProfile.getUser(userId);
    if (user) loadForCuratedUser(user);
  });

  // Initial paint (before UserProfile resolves). The bootstrap event will
  // promptly replace this once /api/users responds.
  renderGuestState();
})();

// ── Movies homepage: "Recommended for you" strip ───────────────────────
(function () {
  const wrap = document.getElementById("strip-wrap");
  const strip = document.getElementById("movie-strip");
  const subtitle = document.getElementById("strip-subtitle");
  if (!wrap || !strip || !window.UserProfile) return;

  let currentFetchId = 0;

  function hide() {
    wrap.hidden = true;
    strip.innerHTML = "";
  }

  function show(user) {
    wrap.hidden = false;
    if (subtitle) {
      subtitle.textContent = `${user.label} · ${user.top_genre}`;
    }
    strip.innerHTML = `<p class="strip-empty">Loading picks for ${escapeHTML(user.label)}…</p>`;
    const fetchId = ++currentFetchId;
    fetch(`/api/recommend/user/${user.id}?n=10`)
      .then((r) => (r.ok ? r.json() : { recommendations: [] }))
      .then((data) => {
        if (fetchId !== currentFetchId) return; // stale; a newer switch happened
        const recs = data.recommendations || [];
        if (recs.length === 0) {
          strip.innerHTML = `<p class="strip-empty">No picks available for this profile.</p>`;
          return;
        }
        strip.innerHTML = recs.map((m, i) => renderMovieCard(m, i)).join("");
        observeCards(Array.from(strip.querySelectorAll(".movie-card")));
        if (window.lucide) lucide.createIcons();
      })
      .catch((err) => {
        if (fetchId !== currentFetchId) return;
        console.error("Strip fetch failed:", err);
        strip.innerHTML = `<p class="strip-empty">Could not load recommendations.</p>`;
      });
  }

  window.addEventListener(window.UserProfile.EVENT, (e) => {
    const { userId, user } = e.detail;
    if (userId == null || !user) {
      hide();
      return;
    }
    show(user);
  });
})();

// ── Movie detail page: personalized predicted rating ───────────────────
(function () {
  const wrap = document.getElementById("stat-predicted");
  const valueEl = document.getElementById("stat-predicted-value");
  if (!wrap || !valueEl || !window.UserProfile) return;

  const movieId = Number(wrap.dataset.movieId);
  if (!Number.isFinite(movieId)) return;

  let fetchSeq = 0;

  function hide() {
    wrap.hidden = true;
  }

  function load(userId) {
    if (userId == null) {
      hide();
      return;
    }
    const seq = ++fetchSeq;
    fetch(`/api/predict_rating/${userId}/${movieId}`)
      .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
      .then(({ ok, data }) => {
        if (seq !== fetchSeq) return; // stale response, newer profile switch in flight
        if (!ok || data.predicted_rating == null) {
          hide();
          return;
        }
        valueEl.textContent = Number(data.predicted_rating).toFixed(1);
        wrap.hidden = false;
      })
      .catch((err) => {
        if (seq !== fetchSeq) return;
        console.error("Predicted rating fetch failed:", err);
        hide();
      });
  }

  // Listen for future profile switches.
  window.addEventListener(window.UserProfile.EVENT, (e) => load(e.detail.userId));

  // Belt-and-braces: even if the bootstrap event fired before this listener
  // attached, ready.then() guarantees we paint the initial state once
  // /api/users has resolved.
  if (window.UserProfile.ready && typeof window.UserProfile.ready.then === "function") {
    window.UserProfile.ready.then(() => load(window.UserProfile.getId()));
  } else {
    load(window.UserProfile.getId());
  }
})();
