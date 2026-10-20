// Search, filter and sort for the reading list. The page is fully rendered
// without this script; it only hides and reorders what's already there.
(() => {
  const list = document.getElementById("list");
  const search = document.getElementById("q");
  const sortSelect = document.getElementById("sort");
  const countEl = document.querySelector(".count");
  const emptyEl = document.querySelector(".empty");
  const clearButtons = document.querySelectorAll(".clear");
  const facetEls = [...document.querySelectorAll(".facet")];
  const facets = facetEls.map((el) => el.dataset.facet);
  const total = list.children.length;

  const words = (s) => (s ? s.split(" ") : []);
  const items = [...list.querySelectorAll(".item")].map((el) => ({
    el,
    values: {
      type: [el.dataset.type],
      origin: words(el.dataset.origin),
      status: [el.dataset.status],
      tags: words(el.dataset.tags),
    },
    added: el.dataset.added,
    published: el.dataset.published,
    title: el.dataset.sortTitle,
    text: el.textContent.toLowerCase().replace(/\s+/g, " "),
  }));

  const state = {
    q: "",
    sort: "added-desc",
    selected: Object.fromEntries(facets.map((f) => [f, new Set()])),
  };

  // Within a facet, chips are OR-ed; across facets they're AND-ed.
  function matches(item, skipFacet) {
    if (state.q && !state.q.split(/\s+/).every((w) => item.text.includes(w))) return false;
    return facets.every((f) => {
      const sel = state.selected[f];
      return f === skipFacet || sel.size === 0 || item.values[f].some((v) => sel.has(v));
    });
  }

  const sorters = {
    "added-desc": (a, b) => b.added.localeCompare(a.added) || a.title.localeCompare(b.title),
    "added-asc": (a, b) => a.added.localeCompare(b.added) || a.title.localeCompare(b.title),
    "published-desc": (a, b) =>
      (b.published || "0").localeCompare(a.published || "0") || a.title.localeCompare(b.title),
    title: (a, b) => a.title.localeCompare(b.title),
  };

  function render() {
    let shown = 0;
    for (const item of items) {
      const visible = matches(item);
      item.el.hidden = !visible;
      if (visible) shown++;
    }

    for (const facetEl of facetEls) {
      const f = facetEl.dataset.facet;
      const pool = items.filter((item) => matches(item, f));
      for (const chip of facetEl.querySelectorAll(".chip")) {
        const v = chip.dataset.value;
        const n = pool.filter((item) => item.values[f].includes(v)).length;
        const pressed = state.selected[f].has(v);
        chip.querySelector(".n").textContent = n;
        chip.setAttribute("aria-pressed", pressed);
        chip.classList.toggle("is-empty", n === 0 && !pressed);
      }
    }

    const filtered = state.q || facets.some((f) => state.selected[f].size);
    countEl.innerHTML = filtered
      ? `<strong>${shown}</strong> of ${total} readings`
      : `<strong>${total}</strong> readings`;
    emptyEl.hidden = shown > 0;
    clearButtons.forEach((b) => (b.hidden = !filtered));
    writeUrl();
  }

  function applySort() {
    [...items].sort(sorters[state.sort]).forEach((item) => list.appendChild(item.el));
  }

  // Keep the current view in the URL so a filtered list can be shared.
  function writeUrl() {
    const params = new URLSearchParams();
    if (state.q) params.set("q", state.q);
    for (const f of facets) if (state.selected[f].size) params.set(f, [...state.selected[f]].join(","));
    if (state.sort !== "added-desc") params.set("sort", state.sort);
    const qs = params.toString();
    history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
  }

  function readUrl() {
    const params = new URLSearchParams(location.search);
    state.q = (params.get("q") || "").trim().toLowerCase();
    search.value = params.get("q") || "";
    for (const f of facets) state.selected[f] = new Set(words((params.get(f) || "").replace(/,/g, " ")));
    if (sorters[params.get("sort")]) state.sort = params.get("sort");
    sortSelect.value = state.sort;
  }

  document.querySelector(".facets").addEventListener("click", (event) => {
    const chip = event.target.closest(".chip");
    if (!chip) return;
    const sel = state.selected[chip.closest(".facet").dataset.facet];
    const v = chip.dataset.value;
    sel.has(v) ? sel.delete(v) : sel.add(v);
    render();
  });

  search.addEventListener("input", () => {
    state.q = search.value.trim().toLowerCase();
    render();
  });

  sortSelect.addEventListener("change", () => {
    state.sort = sortSelect.value;
    applySort();
    render();
  });

  clearButtons.forEach((b) =>
    b.addEventListener("click", () => {
      state.q = "";
      search.value = "";
      facets.forEach((f) => state.selected[f].clear());
      render();
    })
  );

  document.addEventListener("keydown", (event) => {
    const typing = /^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName);
    if (event.key === "/" && !typing) {
      event.preventDefault();
      search.focus();
    } else if (event.key === "Escape" && document.activeElement === search) {
      search.value = "";
      state.q = "";
      render();
    }
  });

  // Theme toggle: flips away from whatever is currently showing.
  document.querySelector(".theme-toggle").addEventListener("click", () => {
    const root = document.documentElement;
    const dark = root.dataset.theme
      ? root.dataset.theme === "dark"
      : matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("theme", root.dataset.theme); } catch (e) {}
  });

  readUrl();
  applySort();
  render();
})();
