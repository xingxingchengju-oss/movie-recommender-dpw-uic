// Guest-only favorites: localStorage-backed list of TMDB ids the user has
// saved from movie detail pages. Loaded on every page (sidebar updates
// universally). Movie detail page and Recommend page consume the public API.
//
// Public surface:  window.Favorites = { KEY, EVENT, getIds, has, add, remove,
//                                       count }
// Event payload:   { ids: number[] } on window for "reelvana:favorites-changed"
(function () {
  const KEY = "reelvana_favorites";
  const EVENT = "reelvana:favorites-changed";

  // Items stored as [{id: int, title: string}, ...] in insertion order.
  // Backwards-compatible: an old value that's a bare array of ints still
  // reads cleanly (titles become "" for those entries until re-saved).
  function readItems() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return [];
      const arr = JSON.parse(raw);
      if (!Array.isArray(arr)) return [];
      const seen = new Set();
      const out = [];
      for (const x of arr) {
        let id, title = "";
        if (typeof x === "number" || typeof x === "string") {
          id = Number(x);
        } else if (x && typeof x === "object") {
          id = Number(x.id);
          title = typeof x.title === "string" ? x.title : "";
        } else {
          continue;
        }
        if (!Number.isFinite(id) || seen.has(id)) continue;
        seen.add(id);
        out.push({ id, title });
      }
      return out;
    } catch (e) {
      console.error("[favorites] localStorage read failed:", e);
      return [];
    }
  }

  function writeItems(items) {
    try {
      localStorage.setItem(KEY, JSON.stringify(items));
    } catch (e) {
      console.error("[favorites] localStorage write failed:", e);
    }
  }

  function dispatch(items) {
    window.dispatchEvent(
      new CustomEvent(EVENT, {
        detail: { items, ids: items.map((it) => it.id) },
      })
    );
  }

  function add(movie) {
    const id = Number(movie && movie.id);
    if (!Number.isFinite(id)) return;
    const items = readItems();
    if (items.some((it) => it.id === id)) return;
    const title = (movie && typeof movie.title === "string") ? movie.title : "";
    items.push({ id, title });
    writeItems(items);
    dispatch(items);
  }

  function remove(id) {
    const n = Number(id);
    if (!Number.isFinite(n)) return;
    const items = readItems().filter((it) => it.id !== n);
    writeItems(items);
    dispatch(items);
  }

  window.Favorites = {
    KEY,
    EVENT,
    getIds: () => readItems().map((it) => it.id),
    getItems: readItems,
    has: (id) => readItems().some((it) => it.id === Number(id)),
    add,
    remove,
    count: () => readItems().length,
  };

  // ─── Sidebar badge: updates label based on profile + favorites count ───
  function updateSidebarBadge() {
    const link = document.getElementById("favorites-link");
    const text = document.getElementById("favorites-count-text");
    if (!link || !text) return;

    const isGuest =
      !window.UserProfile || window.UserProfile.getId() == null;
    const n = readItems().length;

    if (!isGuest) {
      text.textContent = "Switch to Guest to use";
      link.classList.add("is-disabled");
    } else if (n === 0) {
      text.textContent = "No favorites yet";
      link.classList.remove("is-disabled");
    } else {
      text.textContent = `View & recommend (${n})`;
      link.classList.remove("is-disabled");
    }
  }

  function init() {
    updateSidebarBadge();
    window.addEventListener(EVENT, updateSidebarBadge);
    if (window.UserProfile) {
      window.addEventListener(window.UserProfile.EVENT, updateSidebarBadge);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
