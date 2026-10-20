// Search and tag filtering for the reading list. The page is fully
// rendered (in order) without this script; it only hides what doesn't match.
// Every tag is a link like ?tag=labour; clicking one adds it to the active
// filters (all must match), and the current view is kept in the URL.
(() => {
  const KINDS = ["type", "field", "tag", "start"];
  const LABELS = { start: { yes: "start here" } };

  const list = document.getElementById("list");
  const search = document.getElementById("q");
  const countEl = document.querySelector(".count");
  const activeEl = document.querySelector(".active");
  const emptyEl = document.querySelector(".empty");
  const total = list.children.length;

  const split = (s) => (s ? s.split("|") : []);
  const items = [...list.querySelectorAll(".item")].map((el) => ({
    el,
    values: Object.fromEntries(KINDS.map((k) => [k, split(el.dataset[k])])),
    text: el.textContent.toLowerCase().replace(/\s+/g, " "),
  }));

  const state = { q: "", filters: [] }; // filters: [{kind, value}]

  const isActive = (kind, value) => state.filters.some((f) => f.kind === kind && f.value === value);

  function matches(item) {
    if (state.q && !state.q.split(/\s+/).every((w) => item.text.includes(w))) return false;
    return state.filters.every((f) => item.values[f.kind].includes(f.value));
  }

  function render() {
    let shown = 0;
    for (const item of items) {
      const visible = matches(item);
      item.el.hidden = !visible;
      if (visible) shown++;
    }

    const filtered = state.q || state.filters.length;
    countEl.textContent = filtered ? `${shown} of ${total} readings` : `${total} readings`;
    emptyEl.hidden = shown > 0;

    activeEl.hidden = !state.filters.length;
    activeEl.replaceChildren(
      ...state.filters.map(({ kind, value }) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "active-filter";
        b.dataset.kind = kind;
        b.dataset.value = value;
        b.title = "Remove this filter";
        b.innerHTML = `<span></span><span class="x" aria-hidden="true">✕</span>`;
        b.firstChild.textContent = LABELS[kind]?.[value] ?? value;
        return b;
      })
    );
    if (state.filters.length > 1) {
      const clear = document.createElement("button");
      clear.type = "button";
      clear.className = "clear";
      clear.textContent = "clear all";
      activeEl.append(clear);
    }

    for (const a of document.querySelectorAll("a[data-kind]")) {
      a.classList.toggle("is-active", isActive(a.dataset.kind, a.dataset.value));
    }
    writeUrl();
  }

  function writeUrl() {
    const params = new URLSearchParams();
    if (state.q) params.set("q", state.q);
    for (const { kind, value } of state.filters) params.append(kind, value);
    const qs = params.toString();
    history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
  }

  function readUrl() {
    const params = new URLSearchParams(location.search);
    search.value = params.get("q") || "";
    state.q = search.value.trim().toLowerCase();
    state.filters = [];
    for (const kind of KINDS) for (const value of params.getAll(kind)) state.filters.push({ kind, value });
  }

  function toggle(kind, value) {
    state.filters = isActive(kind, value)
      ? state.filters.filter((f) => !(f.kind === kind && f.value === value))
      : [...state.filters, { kind, value }];
    render();
  }

  function clearAll() {
    state.filters = [];
    state.q = "";
    search.value = "";
    render();
  }

  document.addEventListener("click", (event) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    const link = event.target.closest("a[data-kind]");
    const chip = event.target.closest(".active-filter");
    if (link) {
      event.preventDefault();
      toggle(link.dataset.kind, link.dataset.value);
      document.querySelector(".controls").scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (chip) {
      toggle(chip.dataset.kind, chip.dataset.value);
    } else if (event.target.closest(".clear")) {
      clearAll();
    }
  });

  search.addEventListener("input", () => {
    state.q = search.value.trim().toLowerCase();
    render();
  });

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

  readUrl();
  render();
})();
