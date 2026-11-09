/*
 * Nutrislice Menu Card — bundled with the nutrislice_menu integration.
 *
 * Shows breakfast and lunch for one school day with prev/next navigation
 * through every day in the sensors' `menu_by_date` attribute.  Uses only the
 * standard Lovelace custom-card API (setConfig / hass / getCardSize /
 * getGridOptions), so it does not depend on HA frontend internals.
 *
 *   type: custom:nutrislice-menu-card
 *   breakfast_entity: sensor.<school>_menu_breakfast_today
 *   lunch_entity: sensor.<school>_menu_lunch_today
 *   title: School Menu            # optional
 */

const CARD_TYPE = "nutrislice-menu-card";

const MEALS = [
  { key: "breakfast", configKey: "breakfast_entity", title: "🍳 Breakfast" },
  { key: "lunch", configKey: "lunch_entity", title: "🥗 Lunch" },
];

const CATEGORY_LABELS = { vegetable: "Veggie" };

// Placeholder icon for items Nutrislice has no photo for.
const CATEGORY_ICONS = {
  entree: "mdi:silverware-fork-knife",
  condiment: "mdi:soy-sauce",
  vegetable: "mdi:carrot",
  fruit: "mdi:food-apple",
  milk: "mdi:cup",
  grain: "mdi:bread-slice",
  dessert: "mdi:cupcake",
  side: "mdi:bowl-mix",
};
const FALLBACK_ICON = "mdi:food";

const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ESCAPES[c]);
const safeUrl = (url) => (/^https?:\/\//i.test(url || "") ? url : "");

// Menu dates are plain "YYYY-MM-DD" strings in the HA server's local day.
const parseDate = (iso) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
};
const isoDate = (date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;

const STYLE = `
  :host { display: block; }
  .card-content { padding: 16px; }
  .title { font-size: 20px; font-weight: 400; margin-bottom: 8px; color: var(--primary-text-color); }
  .nav { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
  .nav button {
    background: none; border: none; color: var(--primary-text-color);
    font-size: 26px; line-height: 1; cursor: pointer; padding: 4px 12px; border-radius: 8px;
  }
  .nav button:disabled { opacity: 0.3; cursor: default; }
  .nav button:not(:disabled):hover { background: var(--secondary-background-color); }
  .label { flex: 1; text-align: center; font-size: 15px; font-weight: 500; color: var(--primary-text-color); }
  .meal + .meal { margin-top: 16px; }
  .meal-title { font-size: 16px; font-weight: 500; margin-bottom: 8px; color: var(--primary-text-color); }
  .row { display: flex; flex-direction: row; gap: 14px; padding: 4px 0; }
  .row.entrees { margin-bottom: 16px; }
  .tile { display: flex; flex-direction: column; align-items: center; text-align: center; flex: 1 1 0; min-width: 0; }
  .thumb, .ph { width: 100%; aspect-ratio: 1; border-radius: 10px; border: 1px solid var(--divider-color); box-sizing: border-box; }
  .thumb { object-fit: cover; display: block; cursor: zoom-in; }
  .ph {
    background: var(--secondary-background-color); color: var(--secondary-text-color);
    display: flex; align-items: center; justify-content: center; container-type: inline-size;
  }
  .ph ha-icon { --mdc-icon-size: 45cqw; }
  .name { font-size: 12px; font-weight: 500; line-height: 1.25; margin-top: 6px; color: var(--primary-text-color); }
  .name.entree { font-size: 14px; font-weight: 600; }
  .cat { font-size: 10px; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px; }
  .msg { color: var(--secondary-text-color); font-size: 14px; margin: 4px 0; }
  .msg code { font-size: 13px; }
  dialog { padding: 0; border: none; background: transparent; max-width: 90vw; max-height: 90vh; overflow: visible; }
  dialog::backdrop { background: rgba(0, 0, 0, 0.9); }
  dialog img { display: block; max-width: 90vw; max-height: 90vh; border-radius: 8px; cursor: zoom-out; }
`;

class NutrisliceMenuCard extends HTMLElement {
  constructor() {
    super();
    this._config = null;
    this._hass = null;
    this._stateRefs = {};
    this._dates = [];
    this._selected = null;    // date currently shown
    this._defaultDate = null; // sensor's own "next school day"

    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${STYLE}</style><ha-card><div class="card-content"></div></ha-card><dialog><img alt=""></dialog>`;
    this._content = root.querySelector(".card-content");
    this._dialog = root.querySelector("dialog");

    root.addEventListener("click", (ev) => this._onClick(ev));
  }

  setConfig(config) {
    if (!config || (!config.breakfast_entity && !config.lunch_entity)) {
      throw new Error("Set breakfast_entity and/or lunch_entity");
    }
    this._config = config;
    this._stateRefs = {};
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    const ids = this._entityIds();
    const changed = ids.some((id) => hass.states[id] !== this._stateRefs[id]);
    if (!changed) return;
    ids.forEach((id) => { this._stateRefs[id] = hass.states[id]; });
    this._render();
  }

  getCardSize() {
    return 7;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  static getStubConfig(hass) {
    const find = (meal) =>
      Object.keys(hass.states).find((id) => {
        const attrs = hass.states[id].attributes;
        return id.startsWith("sensor.") && attrs.menu_by_date && attrs.meal_type === meal;
      });
    return {
      breakfast_entity: find("breakfast") || "",
      lunch_entity: find("lunch") || "",
    };
  }

  _entityIds() {
    return MEALS.map((m) => this._config[m.configKey]).filter(Boolean);
  }

  _meals() {
    return MEALS.filter((m) => this._config[m.configKey]).map((m) => {
      const entityId = this._config[m.configKey];
      return { ...m, entityId, stateObj: this._hass.states[entityId] };
    });
  }

  _onClick(ev) {
    const target = ev.target;
    if (target.closest("dialog")) {
      this._dialog.close();
    } else if (target.closest("button.prev")) {
      this._step(-1);
    } else if (target.closest("button.next")) {
      this._step(1);
    } else if (target.matches("img.thumb")) {
      this._dialog.querySelector("img").src = target.src;
      this._dialog.showModal();
    }
  }

  _step(dir) {
    const idx = this._dates.indexOf(this._selected) + dir;
    if (idx < 0 || idx >= this._dates.length) return;
    this._selected = this._dates[idx];
    this._render();
  }

  _resolveDates(meals) {
    const all = new Set();
    meals.forEach((m) => Object.keys(m.stateObj?.attributes?.menu_by_date || {}).forEach((d) => all.add(d)));
    this._dates = [...all].sort();

    const sensorDate = meals.map((m) => m.stateObj?.attributes?.date).find(Boolean) || null;
    const todayIso = isoDate(new Date());
    const fallback = this._dates.find((d) => d >= todayIso) || this._dates[this._dates.length - 1] || null;
    const newDefault = this._dates.includes(sensorDate) ? sensorDate : fallback;

    // Follow the sensor's day (e.g. the 9:30 AM flip) unless the user has
    // navigated elsewhere; reset if the shown day dropped out of the window.
    if (!this._selected || this._selected === this._defaultDate || !this._dates.includes(this._selected)) {
      this._selected = newDefault;
    }
    this._defaultDate = newDefault;
  }

  _label(iso) {
    const lang = this._hass?.locale?.language || this._hass?.language || "en-US";
    const day = parseDate(iso);
    const full = day.toLocaleDateString(lang, { weekday: "long", month: "long", day: "numeric" });
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diff = Math.round((day - today) / 86400000);
    if (diff === 0) return `Today — ${full}`;
    if (diff === 1) return `Tomorrow — ${full}`;
    return full;
  }

  _tile(item, isEntree) {
    const img = safeUrl(item.image);
    const category = !isEntree && item.category ? CATEGORY_LABELS[item.category] || item.category : "";
    const icon = CATEGORY_ICONS[item.category] || FALLBACK_ICON;
    return `
      <div class="tile">
        ${img
          ? `<img class="thumb" src="${esc(img)}" loading="lazy" alt="">`
          : `<div class="ph"><ha-icon icon="${icon}"></ha-icon></div>`}
        <div class="name${isEntree ? " entree" : ""}">${esc(item.name)}</div>
        ${category ? `<div class="cat">${esc(category)}</div>` : ""}
      </div>`;
  }

  _mealSection(meal) {
    let body;
    if (!meal.stateObj) {
      body = `<p class="msg">Entity not found: ${esc(meal.entityId)}</p>`;
    } else if (!this._dates.length) {
      body = `<p class="msg">⏳ No menu data yet — call <code>nutrislice_menu.sync_menu</code>.</p>`;
    } else {
      const items = (meal.stateObj.attributes.menu_by_date || {})[this._selected] || [];
      if (!items.length) {
        body = `<p class="msg">No ${esc(meal.key)} served.</p>`;
      } else {
        const entrees = items.filter((i) => i.category === "entree");
        const sides = items.filter((i) => i.category !== "entree");
        body = [
          entrees.length ? `<div class="row entrees">${entrees.map((i) => this._tile(i, true)).join("")}</div>` : "",
          sides.length ? `<div class="row">${sides.map((i) => this._tile(i, false)).join("")}</div>` : "",
        ].join("");
      }
    }
    return `<div class="meal"><div class="meal-title">${esc(meal.title)}</div>${body}</div>`;
  }

  _render() {
    if (!this._config || !this._hass) return;
    const meals = this._meals();
    this._resolveDates(meals);

    const idx = this._dates.indexOf(this._selected);
    const nav = this._selected
      ? `<div class="nav">
           <button class="prev" aria-label="Previous day" ${idx <= 0 ? "disabled" : ""}>‹</button>
           <span class="label">${esc(this._label(this._selected))}</span>
           <button class="next" aria-label="Next day" ${idx >= this._dates.length - 1 ? "disabled" : ""}>›</button>
         </div>`
      : "";

    this._content.innerHTML = [
      this._config.title ? `<div class="title">${esc(this._config.title)}</div>` : "",
      nav,
      ...meals.map((m) => this._mealSection(m)),
    ].join("");
  }
}

if (!customElements.get(CARD_TYPE)) {
  customElements.define(CARD_TYPE, NutrisliceMenuCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: CARD_TYPE,
    name: "Nutrislice Menu",
    description: "School breakfast and lunch menu with day-by-day navigation.",
    preview: true,
    documentationURL: "https://github.com/penguincrest/nutrislice_menu",
  });
}
