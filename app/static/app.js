"use strict";

const API = "";
const STORAGE_KEY = "pcbuilder.selection.v1";
const MULTI = new Set(["ram", "storage"]);

const ICONS = {
  cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3"/>',
  motherboard:
    '<rect x="3" y="3" width="18" height="18" rx="2"/><rect x="7" y="7" width="6" height="6" rx="1"/><path d="M16 7h2M16 10h2M7 16h11"/>',
  ram: '<rect x="3" y="7" width="18" height="8" rx="1.5"/><path d="M7 15v2M11 15v2M15 15v2M17 15v2"/>',
  gpu: '<rect x="2" y="6" width="20" height="10" rx="2"/><circle cx="8" cy="11" r="2.5"/><path d="M14 9h5M14 13h5"/>',
  psu: '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="12" cy="12" r="3.5"/><path d="M12 5v2M12 17v2"/>',
  case: '<rect x="5" y="2" width="14" height="20" rx="2"/><path d="M9 6h6M9 10h6M12 15v3"/>',
  cooler: '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 5v3M12 16v3M5 12h3M16 12h3"/>',
  storage: '<rect x="4" y="4" width="16" height="16" rx="2"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/>',
};

const CATEGORIES = [
  { key: "cpu", label: "Процессор" },
  { key: "motherboard", label: "Плата" },
  { key: "ram", label: "Память" },
  { key: "gpu", label: "Видеокарта" },
  { key: "psu", label: "Блок питания" },
  { key: "case", label: "Корпус" },
  { key: "cooler", label: "Охлаждение" },
  { key: "storage", label: "Накопитель" },
];

const state = {
  category: "cpu",
  search: "",
  components: [],
  total: 0,
  selection: new Map(),
  report: null,
  reportError: null,
  version: null,
  loading: false,
};

const el = {
  slots: document.getElementById("slots"),
  products: document.getElementById("products"),
  search: document.getElementById("search"),
  hint: document.getElementById("catalog-hint"),
  status: document.getElementById("catalog-status"),
  selection: document.getElementById("selection"),
  total: document.getElementById("total"),
  power: document.getElementById("power"),
  psu: document.getElementById("psu"),
  diagnostics: document.getElementById("diagnostics"),
  save: document.getElementById("save"),
  clear: document.getElementById("clear"),
  version: document.getElementById("version"),
  toast: document.getElementById("toast"),
};

const money = new Intl.NumberFormat("ru-RU");

function rub(value) {
  return `${money.format(value)} ₽`;
}

function specChips(component) {
  const chips = [];
  const add = (label, value, suffix = "") => {
    if (value !== null && value !== undefined && value !== "") chips.push(`${label} ${value}${suffix}`);
  };
  add("сокет", component.socket);
  add("память", component.memory_type);
  add("форм-фактор", component.form_factor);
  add("TDP", component.tdp_w, " Вт");
  add("длина", component.length_mm, " мм");
  add("до GPU", component.max_gpu_length_mm, " мм");
  add("мощность", component.wattage_w, " Вт");
  add("объём", component.capacity_gb, " ГБ");
  add("год", component.released_year);
  return chips;
}

async function api(path, options = {}) {
  const response = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(
      body && body.detail ? JSON.stringify(body.detail) : `HTTP ${response.status}`,
    );
    error.status = response.status;
    error.body = body;
    throw error;
  }
  return body;
}

/* ---------- slots ---------- */

function renderSlots(counts = {}) {
  el.slots.replaceChildren();
  for (const category of CATEGORIES) {
    const picked = [...state.selection.values()].filter(
      (item) => item.component.category === category.key,
    );
    const button = document.createElement("button");
    button.type = "button";
    button.className = "slot" + (picked.length ? " is-filled" : "");
    button.setAttribute("aria-pressed", String(state.category === category.key));
    button.addEventListener("click", () => {
      state.category = category.key;
      state.search = "";
      el.search.value = "";
      renderSlots(counts);
      loadComponents();
    });

    const icon = document.createElement("span");
    icon.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[category.key]}</svg>`;

    const name = document.createElement("span");
    name.className = "slot-name";
    name.textContent = category.label;

    const dot = document.createElement("span");
    dot.className = "slot-dot";
    dot.title = picked.length ? "выбрано" : counts[category.key] ? `${counts[category.key]} в каталоге` : "";

    button.append(icon.firstChild, name, dot);
    el.slots.append(button);
  }
}

/* ---------- products ---------- */

function renderStatus(html) {
  if (!html) {
    el.status.hidden = true;
    el.status.replaceChildren();
    return;
  }
  el.status.hidden = false;
  el.status.innerHTML = html;
}

function renderProducts() {
  el.products.replaceChildren();
  if (state.loading) {
    renderStatus("Загрузка каталога…");
    return;
  }
  if (!state.components.length) {
    renderStatus(
      `<strong>Ничего не нашлось</strong>Попробуйте другой запрос или другую категорию.`,
    );
    el.products.hidden = true;
    return;
  }
  renderStatus("");
  el.products.hidden = false;

  for (const component of state.components) {
    const picked = state.selection.get(component.id);
    const card = document.createElement("article");
    card.className = "card" + (picked ? " is-picked" : "");

    const brand = document.createElement("div");
    brand.className = "card-brand";
    brand.textContent = component.brand;

    const model = document.createElement("h3");
    model.className = "card-model";
    model.textContent = component.model;

    const chips = document.createElement("div");
    chips.className = "chips";
    for (const text of specChips(component)) {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = text;
      chips.append(chip);
    }

    const foot = document.createElement("div");
    foot.className = "card-foot";

    const price = document.createElement("span");
    price.className = "price";
    price.textContent = rub(component.price_rub);

    if (picked && MULTI.has(component.category)) {
      foot.append(price, quantityControl(component, picked.quantity));
    } else {
      const add = document.createElement("button");
      add.type = "button";
      add.className = "add";
      add.dataset.picked = String(Boolean(picked));
      add.textContent = picked ? "В сборке" : "Добавить";
      add.setAttribute("aria-pressed", String(Boolean(picked)));
      add.addEventListener("click", () => toggle(component));
      foot.append(price, add);
    }

    card.append(brand, model, chips, foot);
    el.products.append(card);
  }
}

function quantityControl(component, quantity) {
  const wrap = document.createElement("div");
  wrap.className = "qty";

  const minus = document.createElement("button");
  minus.type = "button";
  minus.textContent = "−";
  minus.setAttribute("aria-label", `Убрать одну единицу ${component.model}`);
  minus.addEventListener("click", () => changeQuantity(component, -1));

  const value = document.createElement("span");
  value.textContent = String(quantity);

  const plus = document.createElement("button");
  plus.type = "button";
  plus.textContent = "+";
  plus.setAttribute("aria-label", `Добавить ещё одну единицу ${component.model}`);
  plus.addEventListener("click", () => changeQuantity(component, 1));

  wrap.append(minus, value, plus);
  return wrap;
}

function toggle(component) {
  if (state.selection.has(component.id)) {
    state.selection.delete(component.id);
  } else {
    state.selection.set(component.id, { component, quantity: 1 });
  }
  onChange();
}

function changeQuantity(component, delta) {
  const entry = state.selection.get(component.id);
  if (!entry) return;
  entry.quantity += delta;
  if (entry.quantity <= 0) state.selection.delete(component.id);
  if (entry.quantity > 4) entry.quantity = 4;
  onChange();
}

function onChange() {
  persist();
  syncUrl();
  renderSlots(state.counts || {});
  renderProducts();
  renderSelection();
  scheduleCheck();
}

/* ---------- ссылка на сборку ---------- */

function readIds() {
  const raw = new URLSearchParams(window.location.search).get("ids");
  if (!raw) return [];
  return raw
    .split(",")
    .map((value) => Number(value.trim()))
    .filter((id) => Number.isInteger(id) && id > 0)
    .slice(0, 32);
}

async function applyDeepLink() {
  const ids = readIds();
  if (!ids.length) return false;
  const found = await Promise.all(
    ids.map((id) => api(`/catalog/components/${id}`).catch(() => null)),
  );
  state.selection.clear();
  for (const component of found) {
    if (!component) continue;
    const current = state.selection.get(component.id);
    const quantity = current ? Math.min(current.quantity + 1, 4) : 1;
    state.selection.set(component.id, { component, quantity });
  }
  return state.selection.size > 0;
}

function syncUrl() {
  const ids = [...state.selection.values()].flatMap(({ component, quantity }) =>
    Array.from({ length: quantity }, () => component.id),
  );
  const url = new URL(window.location.href);
  if (ids.length) url.searchParams.set("ids", ids.join(","));
  else url.searchParams.delete("ids");
  window.history.replaceState(null, "", url);
}

/* ---------- selection ---------- */

function renderSelection() {
  el.selection.replaceChildren();
  if (!state.selection.size) {
    const empty = document.createElement("p");
    empty.className = "selection-empty";
    empty.textContent = "Пока пусто. Выберите комплектующие слева.";
    el.selection.append(empty);
  }

  for (const { component, quantity } of state.selection.values()) {
    const row = document.createElement("div");
    row.className = "selection-row";

    const model = document.createElement("span");
    model.className = "sel-model";
    model.textContent = quantity > 1 ? `${component.model} × ${quantity}` : component.model;

    const meta = document.createElement("span");
    meta.className = "sel-meta";
    meta.textContent = `${component.brand} · ${component.category}`;

    const price = document.createElement("span");
    price.className = "sel-price";
    price.textContent = rub(component.price_rub * quantity);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "убрать";
    remove.setAttribute("aria-label", `Убрать ${component.model} из сборки`);
    remove.addEventListener("click", () => {
      state.selection.delete(component.id);
      onChange();
    });

    row.append(model, meta, price, remove);
    el.selection.append(row);
  }
}

function payload() {
  return {
    name: "Сборка из конструктора",
    items: [...state.selection.values()].map(({ component, quantity }) => ({
      component_id: component.id,
      quantity,
    })),
  };
}

/* ---------- compatibility ---------- */

let checkTimer = null;

function scheduleCheck() {
  window.clearTimeout(checkTimer);
  checkTimer = window.setTimeout(runCheck, 260);
}

async function runCheck() {
  if (!state.selection.size) {
    state.report = null;
    state.reportError = null;
    renderSummary();
    return;
  }
  try {
    state.report = await api("/builds/check", {
      method: "POST",
      body: JSON.stringify(payload()),
    });
    state.reportError = null;
  } catch (error) {
    state.report = null;
    state.reportError = error;
  }
  renderSummary();
}

function renderSummary() {
  const localTotal = [...state.selection.values()].reduce(
    (sum, { component, quantity }) => sum + component.price_rub * quantity,
    0,
  );
  const report = state.report;

  el.total.textContent = rub(report ? report.total_price_rub : localTotal);
  el.power.textContent = report ? `${report.estimated_power_w} Вт` : "—";
  el.psu.textContent = report ? `от ${report.recommended_psu_w} Вт` : "—";

  el.diagnostics.replaceChildren();
  if (!state.selection.size) {
    const empty = document.createElement("p");
    empty.className = "diag-empty";
    empty.textContent = "Добавьте комплектующие — совместимость проверится сама.";
    el.diagnostics.append(empty);
    el.save.disabled = true;
    el.save.textContent = "Сохранить сборку";
    return;
  }

  if (state.reportError) {
    const bad = document.createElement("p");
    bad.className = "diag-bad";
    bad.textContent = "Проверка недоступна";
    const hint = document.createElement("p");
    hint.className = "issue-msg";
    hint.textContent = "Сервис не ответил на /builds/check. Обновите страницу или проверьте API.";
    el.diagnostics.append(bad, hint);
    el.save.disabled = true;
    return;
  }

  if (!report) {
    const waiting = document.createElement("p");
    waiting.className = "diag-empty";
    waiting.textContent = "Проверяем совместимость…";
    el.diagnostics.append(waiting);
    el.save.disabled = true;
    return;
  }

  const head = document.createElement("p");
  head.className = report.ok ? "diag-ok" : "diag-bad";
  const mark = document.createElement("span");
  mark.className = "diag-mark";
  mark.textContent = report.ok ? "✓" : "!";
  head.append(
    mark,
    document.createTextNode(
      report.ok ? "Сборка совместима" : `Конфликты: ${report.errors.length}`,
    ),
  );
  el.diagnostics.append(head);

  for (const issue of report.errors) {
    el.diagnostics.append(issueNode(issue, false));
  }
  for (const issue of report.warnings) {
    el.diagnostics.append(issueNode(issue, true));
  }

  el.save.disabled = !report.ok;
  el.save.textContent = report.ok ? "Сохранить сборку" : "Исправьте конфликты";
}

function issueNode(issue, warning) {
  const box = document.createElement("div");
  box.className = "issue" + (warning ? " warn" : "");

  const message = document.createElement("span");
  message.className = "issue-msg";
  message.textContent = issue.message;

  const code = document.createElement("code");
  code.className = "issue-code";
  code.textContent = issue.code;

  box.append(message, code);
  return box;
}

/* ---------- actions ---------- */

function persist() {
  try {
    const data = [...state.selection.values()].map(({ component, quantity }) => ({
      component,
      quantity,
    }));
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    /* приватный режим или запрет storage — работаем без сохранения */
  }
}

function restore() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const data = JSON.parse(raw);
    if (!Array.isArray(data)) return;
    for (const entry of data) {
      if (entry && entry.component && entry.component.id) {
        state.selection.set(entry.component.id, {
          component: entry.component,
          quantity: Math.min(Math.max(Number(entry.quantity) || 1, 1), 4),
        });
      }
    }
  } catch {
    /* повреждённое хранилище — начинаем с пустой сборки */
  }
}

function toast(message, isError = false) {
  el.toast.textContent = message;
  el.toast.classList.toggle("is-error", isError);
  el.toast.hidden = false;
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => {
    el.toast.hidden = true;
  }, 4200);
}

async function save() {
  if (!state.report || !state.report.ok) return;
  el.save.disabled = true;
  el.save.textContent = "Сохраняем…";
  try {
    const build = await api("/builds", { method: "POST", body: JSON.stringify(payload()) });
    toast(`Сборка №${build.id} сохранена · ${rub(build.total_price_rub)}`);
    el.save.textContent = "Сохранить сборку";
    el.save.disabled = false;
  } catch (error) {
    toast(`Не удалось сохранить: HTTP ${error.status || "?"}`, true);
    el.save.textContent = "Сохранить сборку";
    el.save.disabled = false;
  }
}

el.save.addEventListener("click", save);

el.clear.addEventListener("click", () => {
  state.selection.clear();
  onChange();
});

el.search.addEventListener("input", (event) => {
  state.search = event.target.value;
  window.clearTimeout(el.search.timer);
  el.search.timer = window.setTimeout(loadComponents, 260);
});

/* ---------- loading ---------- */

async function loadCounts() {
  try {
    const data = await api("/catalog/categories");
    const counts = {};
    for (const item of data.items) counts[item.category] = item.count;
    state.counts = counts;
    renderSlots(counts);
  } catch {
    /* счётчики не критичны */
  }
}

async function loadComponents() {
  state.loading = true;
  renderProducts();
  const params = new URLSearchParams({ limit: "200" });
  const search = state.search.trim();
  if (search) params.set("search", search);
  else params.set("category", state.category);

  try {
    const data = await api(`/catalog/components?${params}`);
    state.components = data.items;
    state.total = data.total;
    el.hint.textContent = search
      ? `Поиск «${search}»: ${data.total}`
      : `Показано ${data.items.length} из ${data.total}`;
    state.loading = false;
    renderProducts();
  } catch {
    state.loading = false;
    state.components = [];
    el.hint.textContent = "—";
    renderStatus(
      `<strong>Каталог недоступен</strong>Сервис не ответил на /catalog/components. ` +
        `Проверьте, что API запущен: <code>docker compose up -d</code>`,
    );
    el.products.hidden = true;
  }
}

async function loadVersion() {
  try {
    const health = await api("/health");
    state.version = health.version;
    const label = health.version.startsWith("0.0.0") ? "dev" : `v${health.version}`;
    el.version.textContent = health.status === "ok" ? label : "БД недоступна";
  } catch {
    el.version.textContent = "нет связи";
  }
}

async function init() {
  renderSlots();
  renderSelection();
  restore();
  await applyDeepLink();
  renderSelection();
  await Promise.all([loadCounts(), loadVersion()]);
  await loadComponents();
  if (state.selection.size) runCheck();
}

init();
