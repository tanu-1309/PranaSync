// Small DOM helpers. Everything from the workbooks (notes, history text) goes through
// textContent, never innerHTML, so odd characters in patient files cannot inject markup.

const SVG_NS = "http://www.w3.org/2000/svg";

function apply(el, attrs) {
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k.startsWith("aria-") && typeof v === "boolean") { el.setAttribute(k, String(v)); continue; }
    if (v == null || v === false) continue;
    if (k === "class") el.setAttribute("class", v);
    else if (k === "style" && typeof v === "object") {
      for (const [p, val] of Object.entries(v)) p.startsWith("--") ? el.style.setProperty(p, val) : (el.style[p] = val);
    }
    else if (k === "dataset") Object.assign(el.dataset, v);
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2).toLowerCase(), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
}
function append(el, kids) {
  for (const k of kids.flat(Infinity)) {
    if (k == null || k === false) continue;
    el.append(k instanceof Node ? k : document.createTextNode(String(k)));
  }
}
export function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  apply(el, attrs); append(el, kids);
  return el;
}
export function s(tag, attrs, ...kids) {
  const el = document.createElementNS(SVG_NS, tag);
  apply(el, attrs); append(el, kids);
  return el;
}
export const clear = (el) => { while (el.firstChild) el.removeChild(el.firstChild); return el; };

// --------------------------------------------------------------- formatting
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function parseDate(d) { const [y, m, dd] = d.split("-").map(Number); return new Date(Date.UTC(y, m - 1, dd)); }
export const DAY = 86400000;
export function fmtDate(d, mode = "med") {
  if (!d) return "—";
  const t = typeof d === "string" ? parseDate(d) : d;
  const day = t.getUTCDate(), mon = MONTHS[t.getUTCMonth()], yr = t.getUTCFullYear();
  if (mode === "short") return `${day} ${mon}`;
  if (mode === "month") return `${mon} ${yr}`;
  return `${day} ${mon} ${yr}`;
}
export function addDays(d, n) { return new Date(parseDate(d).getTime() + n * DAY); }
export function fmt(v, nd = 1) {
  if (v == null || Number.isNaN(v)) return "—";
  const a = Math.abs(v);
  if (a >= 1000) return Math.round(v).toLocaleString("en-US");
  return Number(v.toFixed(nd)).toString();
}
export const signed = (v, nd = 1) => (v == null ? "—" : (v > 0 ? "+" : v < 0 ? "−" : "") + fmt(Math.abs(v), nd));
export const pct = (v, nd = 0) => (v == null ? "—" : `${(v * 100).toFixed(nd)}%`);

// Tiny markdown: paragraphs, **bold**, _italic_ — what the explainer templates emit.
export function md(text) {
  const inline = (el, str) => {
    str.split(/(\*\*[^*]+\*\*|_[^_]+_)/g).forEach((part) => {
      if (part.startsWith("**")) el.append(h("strong", null, part.slice(2, -2)));
      else if (part.startsWith("_") && part.endsWith("_") && part.length > 2) el.append(h("em", null, part.slice(1, -1)));
      else el.append(part);
    });
    return el;
  };
  return String(text || "").split(/\n{2,}/).flatMap((para) => {
    const out = [];
    let prose = [], items = [];
    const flush = () => {
      if (prose.length) out.push(inline(h("p"), prose.join(" "))); prose = [];
      if (items.length) out.push(h("ul", { class: "bullets" }, items.map((i) => inline(h("li"), i)))); items = [];
    };
    para.split("\n").forEach((line) => {
      if (/^\s*[-•]\s+/.test(line)) { if (prose.length) flush(); items.push(line.replace(/^\s*[-•]\s+/, "")); }
      else { if (items.length) flush(); if (line.trim()) prose.push(line.trim()); }
    });
    flush();
    return out;
  });
}

// --------------------------------------------------------------- vocabulary
export const STATUS = {
  pattern_with_context: { label: "Pattern · linked to history", short: "Pattern + history", tone: "ember", rank: 0 },
  pattern_no_context: { label: "Pattern · no history link", short: "Pattern", tone: "gold", rank: 1 },
  known_context_stable: { label: "History noted · stable", short: "Stable", tone: "teal", rank: 2 },
  no_pattern: { label: "No pattern", short: "No pattern", tone: "slate", rank: 3 },
  insufficient_data: { label: "Not enough data", short: "Too little data", tone: "faint", rank: 4 },
  not_applicable: { label: "Not applicable", short: "N/A", tone: "faint", rank: 5 },
};
export const AREAS = {
  t2d: { name: "Metabolic health", sub: "Type 2 diabetes risk", icon: "drop" },
  htn: { name: "Cardiovascular", sub: "Hypertension risk", icon: "heart" },
  pcos: { name: "Women’s health", sub: "PCOS", icon: "cycle" },
};
export const chip = (status) => {
  const m = STATUS[status] || STATUS.no_pattern;
  return h("span", { class: `mark tone-${m.tone} ${status === "insufficient_data" || status === "not_applicable" ? "hollow" : ""}` }, m.label);
};

const ICONS = {
  drop: "M12 3.2c3.4 4.4 6 7.4 6 10.4A6 6 0 0 1 6 13.6c0-3 2.6-6 6-10.4Z",
  heart: "M12 20s-7-4.4-7-10a4.1 4.1 0 0 1 7-2.9A4.1 4.1 0 0 1 19 10c0 5.6-7 10-7 10Z",
  cycle: "M20 12a8 8 0 1 1-2.4-5.7M20 4v4h-4",
  search: "M11 18a7 7 0 1 1 0-14 7 7 0 0 1 0 14Zm9 3-4.3-4.3",
  moon: "M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z",
  sun: "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0-15v2m0 16v2M4.2 4.2l1.4 1.4m12.8 12.8 1.4 1.4M2 12h2m16 0h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
  info: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Zm0-11v6m0-9.5v.01",
  arrowUp: "M12 19V5m-6 6 6-6 6 6",
  arrowDown: "M12 5v14m6-6-6 6-6-6",
  arrowRight: "M5 12h14m-6-6 6 6-6 6",
  question: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20ZM9.5 9.5a2.5 2.5 0 1 1 3.6 2.2c-.7.4-1.1 1-1.1 1.8M12 17v.01",
  check: "M20 6 9 17l-5-5",
  x: "M18 6 6 18M6 6l12 12",
  shield: "M12 22s8-3.5 8-10V5l-8-3-8 3v7c0 6.5 8 10 8 10Z",
  pill: "M10.5 20.5 3.5 13.5a5 5 0 0 1 7-7l7 7a5 5 0 0 1-7 7ZM8.5 8.5l7 7",
  flask: "M9 3h6M10 3v6L4.5 19a1.5 1.5 0 0 0 1.3 2.2h12.4a1.5 1.5 0 0 0 1.3-2.2L14 9V3",
  upload: "M12 16V4m-5 5 5-5 5 5M4 20h16",
  trash: "M4 7h16M10 11v6m4-6v6M6 7l1 13h10l1-13M9 7V4h6v3",
  print: "M7 9V3h10v6M7 17H4v-7h16v7h-3M7 14h10v7H7z",
  wave: "M3 12c3-6 5-6 9 0s6 6 9 0",
};
export function icon(name, size = 18, sw = 1.8) {
  return s("svg", { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": sw, "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true" },
    s("path", { d: ICONS[name] || ICONS.info }));
}

export function logo(size = 34) {
  return s("svg", { width: size, height: size, viewBox: "0 0 32 32", "aria-hidden": "true" },
    s("rect", { width: 32, height: 32, style: { fill: "var(--ink)" } }),
    s("path", { d: "M4 21c4-8 8-8 12 0s8 8 12 0", fill: "none", "stroke-width": 2, style: { stroke: "var(--bg)" } }),
    s("path", { d: "M4 13c4-6 8-6 12 0s8 6 12 0", fill: "none", "stroke-width": 2, style: { stroke: "var(--ember)" } }));
}

// --------------------------------------------------------------- tooltip
let tipEl;
export const tip = {
  show(node, x, y) {
    if (!tipEl) { tipEl = h("div", { class: "tip", role: "tooltip" }); document.body.append(tipEl); }
    clear(tipEl); tipEl.append(node);
    tipEl.classList.add("on");
    const w = tipEl.offsetWidth, hh = tipEl.offsetHeight;
    let left = x + 16, top = y + 16;
    if (left + w > innerWidth - 10) left = x - w - 16;
    if (top + hh > innerHeight - 10) top = y - hh - 16;
    tipEl.style.left = `${Math.max(8, left)}px`; tipEl.style.top = `${Math.max(8, top)}px`;
  },
  hide() { tipEl?.classList.remove("on"); },
};

// --------------------------------------------------------------- data
export class ApiError extends Error { constructor(msg, status) { super(msg); this.status = status; } }
const cache = new Map();
export async function api(path, { fresh = false, method = "GET", body } = {}) {
  if (!fresh && method === "GET" && cache.has(path)) return cache.get(path);
  const p = fetch(`/api/${path}`, {
    method, credentials: "same-origin",
    headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined,
  }).then(async (r) => {
    if (!r.ok) { const j = await r.json().catch(() => ({})); throw new ApiError(j.detail || `Server error ${r.status}`, r.status); }
    return r.json();
  });
  if (method === "GET") { cache.set(path, p); p.catch(() => cache.delete(path)); }
  return p;
}
export const forgetCache = () => cache.clear();
export const skeleton = (h_ = 120) => h("div", { class: "skeleton", style: { height: `${h_}px` }, "aria-hidden": "true" });
