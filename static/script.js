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

function renderMovieCard(m, indexOffset, explanation) {
  const poster = m.poster_url
    ? `<div class="movie-poster" style="background-image:url('${m.poster_url}');background-size:cover;background-position:center"></div>`
    : `<div class="movie-poster" style="background:${getPosterGradient(m.id)}">
         <i data-lucide="film" class="poster-icon"></i>
       </div>`;
  const rating = m.vote_average != null ? m.vote_average.toFixed(1) : "—";
  const year = m.release_year != null ? m.release_year : "—";
  const delay = ((indexOffset || 0) % 24) * 0.04;
  // Optional "Because you saved X (sim Y.YY)" annotation — V2C hybrid recs.
  const explainBlock = explanation && explanation.source_title
    ? `<div class="fav-explain">Because you saved <span class="fav-explain-source">${escapeHTML(explanation.source_title)}</span> · sim ${explanation.sim.toFixed(2)}</div>`
    : "";
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
      ${explainBlock}
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

// ── Recommender page: tab switching (with URL hash support) ────────────
(function () {
  const tabs = document.querySelectorAll(".rec-tab");
  const panels = document.querySelectorAll(".rec-tab-panel");
  if (!tabs.length) return;

  function activate(target) {
    let matched = false;
    tabs.forEach((t) => {
      const active = t.dataset.tab === target;
      t.classList.toggle("active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
      if (active) matched = true;
    });
    if (!matched) return false;
    panels.forEach((p) => {
      const active = p.id === `tab-${target}`;
      p.classList.toggle("active", active);
      p.hidden = !active;
    });
    return true;
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => activate(tab.dataset.tab));
  });

  // Activate from URL hash like "#tab=from-favorites" on page load.
  const hashMatch = window.location.hash.match(/^#tab=([\w-]+)/);
  if (hashMatch) activate(hashMatch[1]);
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
// Three modes, always visible:
//   - Curated profile  → SVD picks for that user (/api/recommend/user/<id>)
//   - Guest + favorites → Hybrid picks at α=0.5 (/api/recommend/build)
//   - Guest + no favorites → friendly CTA empty state
(function () {
  const wrap = document.getElementById("strip-wrap");
  const strip = document.getElementById("movie-strip");
  const subtitle = document.getElementById("strip-subtitle");
  if (!wrap || !strip || !window.UserProfile || !window.Favorites) return;

  let fetchSeq = 0;

  function renderEmptyCta() {
    wrap.hidden = false;
    if (subtitle) subtitle.textContent = "";
    strip.innerHTML = `
      <div class="strip-empty-cta">
        <span class="strip-empty-cta-icon" aria-hidden="true">♡</span>
        <p class="strip-empty-cta-text">
          Save a film from its detail page and we'll line up picks here based on your taste.
        </p>
      </div>`;
  }

  function renderCards(recs, label, explanations) {
    wrap.hidden = false;
    if (subtitle) subtitle.textContent = label || "";
    if (!recs.length) {
      strip.innerHTML = `<p class="strip-empty">No picks available right now.</p>`;
      return;
    }
    strip.innerHTML = recs
      .map((m, i) => {
        const ex = explanations && (explanations[m.id] || explanations[String(m.id)]);
        return renderMovieCard(m, i, ex);
      })
      .join("");
    observeCards(Array.from(strip.querySelectorAll(".movie-card")));
    if (window.lucide) lucide.createIcons();
  }

  function loadCurated(user) {
    wrap.hidden = false;
    const label = `${user.label} · ${user.top_genre}`;
    if (subtitle) subtitle.textContent = label;
    strip.innerHTML = `<p class="strip-empty">Loading picks for ${escapeHTML(user.label)}…</p>`;
    const seq = ++fetchSeq;
    fetch(`/api/recommend/user/${user.id}?n=10`)
      .then((r) => (r.ok ? r.json() : { recommendations: [] }))
      .then((data) => {
        if (seq !== fetchSeq) return;
        renderCards(data.recommendations || [], label);
      })
      .catch((err) => {
        if (seq !== fetchSeq) return;
        console.error("Strip curated fetch failed:", err);
        strip.innerHTML = `<p class="strip-empty">Could not load recommendations.</p>`;
      });
  }

  function loadFavorites(items) {
    wrap.hidden = false;
    const n = items.length;
    const label = `Based on your ${n} favorite${n === 1 ? "" : "s"}`;
    if (subtitle) subtitle.textContent = label;
    strip.innerHTML = `<p class="strip-empty">Blending content and collaborative signals…</p>`;
    const seq = ++fetchSeq;
    fetch("/api/recommend/build", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ movie_ids: items.map((it) => it.id), alpha: 0.5, n: 10 }),
    })
      .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
      .then(({ ok, data }) => {
        if (seq !== fetchSeq) return;
        if (!ok) {
          strip.innerHTML = `<p class="strip-empty">${escapeHTML(data.hint || data.error || "Could not load recommendations.")}</p>`;
          return;
        }
        renderCards(data.recommendations || [], label, data.explanations || {});
      })
      .catch((err) => {
        if (seq !== fetchSeq) return;
        console.error("Strip favorites fetch failed:", err);
        strip.innerHTML = `<p class="strip-empty">Could not load recommendations.</p>`;
      });
  }

  function refresh() {
    const userId = window.UserProfile.getId();
    if (userId != null) {
      const user = window.UserProfile.getUser(userId);
      if (user) loadCurated(user);
      return;
    }
    // Guest mode.
    const items = window.Favorites.getItems();
    if (items.length === 0) {
      renderEmptyCta();
      return;
    }
    loadFavorites(items);
  }

  window.addEventListener(window.UserProfile.EVENT, refresh);
  window.addEventListener(window.Favorites.EVENT, refresh);

  // Initial paint after /api/users resolves so getUser() can find the cache.
  if (window.UserProfile.ready && typeof window.UserProfile.ready.then === "function") {
    window.UserProfile.ready.then(refresh);
  } else {
    refresh();
  }
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

// ── Movie detail: Save to favorites button (V2C) ───────────────────────
(function () {
  const action = document.querySelector(".fav-action");
  const btn = document.getElementById("fav-btn");
  const hint = document.getElementById("fav-hint");
  if (!action || !btn || !window.Favorites) return;

  const movieId = Number(action.dataset.movieId);
  const movieTitle = String(action.dataset.movieTitle || "");
  if (!Number.isFinite(movieId)) return;

  const iconEl = btn.querySelector(".fav-btn-icon");
  const labelEl = btn.querySelector(".fav-btn-label");

  function showHint(msg, durationMs) {
    if (!hint) return;
    hint.textContent = msg;
    hint.hidden = false;
    if (durationMs) {
      setTimeout(() => {
        if (hint.textContent === msg) hint.hidden = true;
      }, durationMs);
    }
  }

  function paint() {
    const saved = window.Favorites.has(movieId);
    btn.classList.toggle("is-saved", saved);
    if (iconEl) iconEl.textContent = saved ? "♥" : "♡";
    if (labelEl) labelEl.textContent = saved ? "Saved" : "Save to favorites";
    btn.setAttribute("aria-pressed", saved ? "true" : "false");
  }

  btn.addEventListener("click", () => {
    if (window.Favorites.has(movieId)) {
      window.Favorites.remove(movieId);
      paint();
      return;
    }
    // If a curated profile is active, auto-switch to Guest so the favorite
    // is meaningful (favorites are Guest-only by product design).
    if (window.UserProfile && window.UserProfile.getId() != null) {
      window.UserProfile.setId(null);
      showHint("Switched to Guest — your favorites apply here.", 4000);
    }
    window.Favorites.add({ id: movieId, title: movieTitle });
    paint();
  });

  window.addEventListener(window.Favorites.EVENT, paint);
  paint();
})();

// ── Recommender page: From Favorites tab — hybrid recommender (V2C) ────
(function () {
  const stateCurated = document.getElementById("fav-empty-curated");
  const stateZero = document.getElementById("fav-empty-zero");
  const stateBody = document.getElementById("fav-body");
  const chipsBox = document.getElementById("fav-chips");
  const alphaInput = document.getElementById("fav-alpha");
  const alphaReadout = document.getElementById("fav-alpha-readout");
  const submitBtn = document.getElementById("fav-submit");
  const noteEl = document.getElementById("fav-note");
  const resultsGrid = document.getElementById("fav-results");
  const switchGuestBtn = document.getElementById("fav-switch-guest");
  if (!stateCurated || !stateZero || !stateBody || !chipsBox || !alphaInput || !submitBtn || !resultsGrid) return;
  if (!window.Favorites || !window.UserProfile) return;

  let submitSeq = 0;
  // Signature of the favorites set last successfully fetched. Used to skip
  // duplicate auto-submits when the user just tab-hops without changing
  // their list. NOTE: alpha is intentionally NOT part of the signature —
  // dragging the slider shouldn't fire a request, the user clicks Find.
  let lastFetchedSig = "";

  function currentSig() {
    return window.Favorites.getIds().slice().sort((a, b) => a - b).join(",");
  }

  function setNote(msg, kind) {
    if (!msg) {
      noteEl.hidden = true;
      noteEl.textContent = "";
      noteEl.classList.remove("is-err");
      return;
    }
    noteEl.textContent = msg;
    noteEl.classList.toggle("is-err", kind === "err");
    noteEl.hidden = false;
  }

  function showState(which) {
    stateCurated.hidden = which !== "curated";
    stateZero.hidden = which !== "zero";
    stateBody.hidden = which !== "body";
  }

  function renderChips() {
    const items = window.Favorites.getItems();
    if (!items.length) {
      chipsBox.innerHTML = "";
      return;
    }
    chipsBox.innerHTML = items
      .map((it) => {
        const title = it.title || `#${it.id}`;
        return `
          <span class="fav-chip" data-id="${it.id}">
            <span class="fav-chip-title">${escapeHTML(title)}</span>
            <button type="button" class="fav-chip-remove" aria-label="Remove ${escapeHTML(title)}">×</button>
          </span>`;
      })
      .join("");
  }

  function decideState() {
    const userId = window.UserProfile.getId();
    if (userId != null) {
      showState("curated");
      return;
    }
    if (window.Favorites.count() === 0) {
      showState("zero");
      // If the user just cleared their favorites, also clear stale results.
      resultsGrid.innerHTML = "";
      lastFetchedSig = "";
      return;
    }
    renderChips();
    showState("body");
    // Auto-fetch when the favorites set has changed since the last
    // successful fetch (first visit, add/remove chip, etc.). Tab-hops with
    // no change reuse the cached grid silently.
    if (currentSig() !== lastFetchedSig) submit();
  }

  function updateAlphaReadout() {
    const a = Number(alphaInput.value) / 100;
    alphaReadout.textContent = a.toFixed(2);
  }

  function submit() {
    const items = window.Favorites.getItems();
    if (!items.length) return;
    const alpha = Number(alphaInput.value) / 100;
    const body = { movie_ids: items.map((it) => it.id), alpha, n: 20 };
    const sig = currentSig();

    setNote("");
    resultsGrid.innerHTML = `<p class="empty-note">Blending content and collaborative signals…</p>`;
    const seq = ++submitSeq;

    fetch("/api/recommend/build", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
      .then(({ ok, data }) => {
        if (seq !== submitSeq) return;
        if (!ok) {
          setNote(data.hint || data.error || "Could not build recommendations.", "err");
          resultsGrid.innerHTML = "";
          return;
        }
        const recs = data.recommendations || [];
        const ignored = data.ignored_ids || [];
        const used = data.used_ids || [];
        const explanations = data.explanations || {};

        if (!recs.length && data.hint) {
          setNote(data.hint);
        } else if (ignored.length) {
          const total = used.length + ignored.length;
          setNote(`Used ${used.length}/${total} of your favorites — the others have no recommendation signal.`);
        }

        if (!recs.length) {
          resultsGrid.innerHTML = `<p class="empty-note">No recommendations available.</p>`;
          return;
        }
        resultsGrid.innerHTML = recs
          .map((m, i) => renderMovieCard(m, i, explanations[m.id] || explanations[String(m.id)]))
          .join("");
        observeCards(Array.from(resultsGrid.querySelectorAll(".movie-card")));
        if (window.lucide) lucide.createIcons();
        lastFetchedSig = sig;
      })
      .catch((err) => {
        if (seq !== submitSeq) return;
        console.error("Hybrid fetch failed:", err);
        setNote("Could not load recommendations.", "err");
        resultsGrid.innerHTML = "";
      });
  }

  // Chip remove
  chipsBox.addEventListener("click", (e) => {
    const removeBtn = e.target.closest(".fav-chip-remove");
    if (!removeBtn) return;
    const chip = removeBtn.closest(".fav-chip");
    if (!chip) return;
    window.Favorites.remove(chip.dataset.id);
    // Note: reelvana:favorites-changed will trigger decideState() below.
  });

  // α slider
  alphaInput.addEventListener("input", updateAlphaReadout);
  submitBtn.addEventListener("click", submit);

  // State A CTA — switch back to Guest
  if (switchGuestBtn) {
    switchGuestBtn.addEventListener("click", () => {
      window.UserProfile.setId(null);
    });
  }

  // React to global events
  window.addEventListener(window.UserProfile.EVENT, decideState);
  window.addEventListener(window.Favorites.EVENT, decideState);

  // Initial paint
  updateAlphaReadout();
  decideState();
})();

// (The V2B3 Build Your Own IIFE — search + autocomplete + chips + α-less
//  submit + genre filter — was removed in V2C. The replacement above reads
//  saved films directly from localStorage and routes through the hybrid
//  recommender at /api/recommend/build.)
