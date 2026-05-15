// Global "Viewing As" profile state, sidebar UI, and event bus.
// Loaded on every page (including analysis.html, which does not load script.js).
(function () {
  const KEY = "reelvana_user_id";
  const EVENT = "reelvana:user-changed";

  let cachedUsers = null;

  function readStoredId() {
    const raw = localStorage.getItem(KEY);
    if (raw == null || raw === "" || raw === "guest") return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  }

  function writeStoredId(id) {
    if (id == null) {
      localStorage.removeItem(KEY);
    } else {
      localStorage.setItem(KEY, String(id));
    }
  }

  function escapeHTML(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
    })[c]);
  }

  function getUserById(id) {
    if (id == null || !cachedUsers) return null;
    return cachedUsers.find((u) => u.id === id) || null;
  }

  function applyActiveState(activeId) {
    const list = document.getElementById("profile-list");
    if (!list) return;
    list.querySelectorAll(".profile-row").forEach((row) => {
      const rowId = row.dataset.profileId;
      const isActive =
        (activeId == null && rowId === "guest") ||
        (activeId != null && rowId === String(activeId));
      row.classList.toggle("active", isActive);
    });
  }

  function dispatchChange(userId) {
    const user = getUserById(userId);
    window.dispatchEvent(new CustomEvent(EVENT, { detail: { userId, user } }));
  }

  function setId(id) {
    // Treat null/undefined/"guest" as Guest.
    const normalized = id == null || id === "guest" ? null : Number(id);
    writeStoredId(normalized);
    applyActiveState(normalized);
    dispatchChange(normalized);
  }

  function renderCuratedRows(users) {
    const list = document.getElementById("profile-list");
    if (!list) return;
    // Remove any previously-rendered curated rows; keep the static Guest row.
    list.querySelectorAll(".profile-row.curated").forEach((el) => el.parentElement.remove());

    const html = users
      .map(
        (u) => `
        <li>
          <button type="button" class="profile-row curated" data-profile-id="${u.id}">
            <span class="profile-radio" aria-hidden="true"></span>
            <span class="profile-meta">
              <span class="profile-label">${escapeHTML(u.label)}</span>
              <span class="profile-sub">${escapeHTML(u.top_genre)} · ${u.n_ratings} ratings</span>
            </span>
          </button>
        </li>`
      )
      .join("");
    list.insertAdjacentHTML("beforeend", html);
  }

  function wireClicks() {
    const list = document.getElementById("profile-list");
    if (!list) return;
    list.addEventListener("click", (e) => {
      const row = e.target.closest(".profile-row");
      if (!row) return;
      const raw = row.dataset.profileId;
      setId(raw === "guest" ? null : Number(raw));
    });
  }

  function loadUsers() {
    return fetch("/api/users")
      .then((r) => (r.ok ? r.json() : { users: [] }))
      .then((data) => {
        cachedUsers = Array.isArray(data.users) ? data.users : [];
        return cachedUsers;
      })
      .catch((err) => {
        console.error("[user_profile] /api/users failed:", err);
        cachedUsers = [];
        return cachedUsers;
      });
  }

  // Public API.
  window.UserProfile = {
    KEY,
    EVENT,
    getId: readStoredId,
    setId,
    getUser: getUserById,
    getUsers: () => cachedUsers,
    ready: null, // promise resolved once /api/users has returned
  };

  // Bootstrap. Guest row is already in the DOM via the Jinja partial, so the
  // sidebar is usable immediately. Curated rows + initial event fire once
  // /api/users resolves.
  wireClicks();
  // Show the stored selection's active state on Guest immediately (if Guest).
  // The curated row's active class is applied after rendering.
  applyActiveState(readStoredId());

  window.UserProfile.ready = loadUsers().then((users) => {
    renderCuratedRows(users);

    // If the stored ID points to a user no longer in the curated list, clear it.
    let stored = readStoredId();
    if (stored != null && !getUserById(stored)) {
      writeStoredId(null);
      stored = null;
    }
    applyActiveState(stored);

    if (window.lucide) lucide.createIcons();
    dispatchChange(stored);
    return users;
  });
})();
