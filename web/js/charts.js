// Hand-drawn charts. No chart library: the convergence map is a CSS grid, the rest is plain SVG.
import { h, s, clear, fmt, signed, fmtDate, parseDate, addDays, DAY, tip, icon } from "./ui.js";

// ------------------------------------------------------------------ helpers
function weekly(series, weeks) {
  const { v, base } = series;
  const sd = Math.max((base.hi - base.lo) / 2, 1e-6);
  const out = [];
  for (let w = 0; w < weeks; w++) {
    let sum = 0, n = 0;
    for (let i = w * 7; i < Math.min(v.length, (w + 1) * 7); i++) if (v[i] != null) { sum += v[i]; n++; }
    out.push(n >= 2 ? { mean: sum / n, z: (sum / n - base.mean) / sd } : null);
  }
  return out;
}
const dirOf = (p, key) => {
  for (const sc of p.scenarios) if (sc.signals?.[key]?.direction) return sc.signals[key].direction;
  return null;
};
export const patternSignals = (p) => new Set(p.scenarios.flatMap((s) => (s.surfaced ? s.pattern_signals : [])));
export function onsets(p) {
  const seen = new Map();
  for (const sc of p.scenarios) if (sc.surfaced && sc.pattern_start) {
    const arr = seen.get(sc.pattern_start) || [];
    arr.push(sc.scenario); seen.set(sc.pattern_start, arr);
  }
  return [...seen].map(([date, areas]) => ({ date, areas }));
}
const pos = (p, date, n) => ((parseDate(date) - parseDate(p.start)) / DAY + 0.5) / n;

// ------------------------------------------------------------------ convergence map
export function convergence(p, { compact = false } = {}) {
  const hits = patternSignals(p);
  const rows = [];
  for (const sc of p.scenarios) for (const key of Object.keys(sc.signals || {})) {
    if (!p.series[key] || rows.some((r) => r.key === key)) continue;
    rows.push({ key, dir: dirOf(p, key), hit: hits.has(key), meta: p.series[key] });
  }
  rows.sort((a, b) => b.hit - a.hit);
  const n = Math.max(...rows.map((r) => r.meta.n), 0);
  const W = Math.ceil(n / 7);
  const root = h("div", { class: "cm", style: { "--w": W } });
  if (!rows.length) return h("p", { class: "muted" }, "No daily signals are available for this person.");

  const wk = rows.map((r) => weekly(r.meta, W));
  const cval = (r, c) => (c == null ? null : (r.dir === "down" ? -c.z : c.z));

  // event rail
  const rail = h("div", { class: "rail2" });
  if (!compact) {
    rail.append(h("span", { class: "lane-l", style: { top: "0" } }, "Medication"),
      h("span", { class: "lane-l", style: { top: "30px" } }, "Symptoms"),
      h("span", { class: "lane-l", style: { top: "44px" } }, "Notes"));
    let lastLabel = -100;
    for (const m of [...p.meds].sort((a, b) => (a.start || "").localeCompare(b.start || ""))) {
      if (!m.start || parseDate(m.start) < parseDate(p.start)) continue;
      const x = pos(p, m.start, n) * 100;
      const crowded = x - lastLabel < 13;   // too close to the previous name: show the name on hover instead of overlapping
      if (!crowded) lastLabel = x;
      const b = h("button", { class: `ev med${crowded ? " tight" : ""}`, style: { left: `${x}%` }, "aria-label": `${m.name} ${m.dose}, ${m.status}, started ${fmtDate(m.start)}` }, h("i"), h("span", null, m.name.split(" ")[0]));
      b.addEventListener("pointerenter", (e) => tip.show(h("div", null, h("b", null, `${m.name} · ${m.dose}`), h("div", null, `Started ${fmtDate(m.start)}`), h("div", null, `${m.for} · ${m.status}`)), e.clientX, e.clientY));
      b.addEventListener("pointerleave", tip.hide);
      rail.append(b);
    }
    for (const e of p.events) {
      if (e.t !== "symptoms" && e.t !== "notes") continue;
      if (parseDate(e.d) < parseDate(p.start)) continue;
      const b = h("button", { class: `ev ${e.t === "symptoms" ? "sym" : "note"}`, style: { left: `${pos(p, e.d, n) * 100}%` }, "aria-label": `${e.t === "symptoms" ? "Symptom" : "Clinical note"} ${fmtDate(e.d)}: ${e.text}` });
      b.addEventListener("pointerenter", (ev) => tip.show(h("div", null, h("b", null, e.t === "symptoms" ? "Symptom logged" : "Clinical note"), h("div", null, e.text), h("div", { style: { opacity: .7, marginTop: "4px" } }, fmtDate(e.d))), ev.clientX, ev.clientY));
      b.addEventListener("pointerleave", tip.hide);
      rail.append(b);
    }
  } else rail.style.height = "6px";

  // grid
  const grid = h("div", { class: "grid" });
  rows.forEach((r, ri) => {
    const row = h("div", { class: "crow" }, h("span", { class: `rl ${r.hit ? "hit" : ""}` }, r.meta.label));
    wk[ri].forEach((c) => {
      const cv = cval(r, c);
      const cell = h("span", { class: "cell" });
      if (cv == null) cell.style.background = "color-mix(in srgb, var(--cell-neutral) 40%, transparent)";
      else {
        const t = Math.min(1, Math.abs(cv) / 3);
        cell.style.background = cv > 0
          ? `color-mix(in srgb, var(--ember) ${Math.round(t * 100)}%, var(--cell-neutral))`
          : `color-mix(in srgb, var(--teal) ${Math.round(t * 75)}%, var(--cell-neutral))`;
      }
      row.append(cell);
    });
    grid.append(row);
  });

  const hair = h("div", { class: "hair" });
  const axis = h("div", { class: "axis" });
  const start = parseDate(p.start);
  for (let m = 0; m < 14; m++) {
    const d = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + m, 1));
    const idx = (d - start) / DAY;
    if (idx < 0 || idx > n - 5) continue;
    axis.append(h("span", { style: { left: `${(idx / n) * 100}%` } }, fmtDate(d, "short").split(" ")[1] + (d.getUTCMonth() === 0 ? ` ’${String(d.getUTCFullYear()).slice(2)}` : "")));
  }

  root.append(rail, grid, axis, hair);
  const lab = "var(--lab)";
  const xCalc = (f) => `calc(${lab} + (100% - ${lab}) * ${f})`;
  for (const o of onsets(p)) {
    const f = pos(p, o.date, n);
    if (f < 0 || f > 1) continue;
    root.append(h("div", { class: "onset", style: { left: xCalc(f) } },
      h("b", null, `Pattern begins · ${fmtDate(o.date, "short")}`)));
  }

  // hover
  grid.addEventListener("pointermove", (e) => {
    const rect = grid.getBoundingClientRect();
    const labW = parseFloat(getComputedStyle(root).getPropertyValue("--lab")) || 0;
    const x = e.clientX - rect.left;
    const wi = Math.max(0, Math.min(W - 1, Math.floor((x / rect.width) * W)));
    hair.style.left = xCalc((wi + 0.5) / W); hair.style.opacity = ".35";
    const d0 = addDays(p.start, wi * 7), d1 = addDays(p.start, Math.min(n - 1, wi * 7 + 6));
    const body = h("div", null, h("b", null, `${fmtDate(d0, "short")} – ${fmtDate(d1)}`));
    rows.forEach((r, ri) => {
      const c = wk[ri][wi];
      if (!c) return;
      const dv = c.mean - r.meta.base.mean;
      body.append(h("div", { class: "tr" }, h("span", null, h("i", { class: "sw2", style: { background: cval(r, c) > 1 ? "var(--ember)" : cval(r, c) < -1 ? "var(--teal)" : "#b9a9c8" } }), r.meta.label),
        h("span", null, `${fmt(c.mean)} (${signed(dv)})`)));
    });
    tip.show(body, e.clientX, e.clientY);
  });
  grid.addEventListener("pointerleave", () => { hair.style.opacity = "0"; tip.hide(); });
  return root;
}

export function convergenceKey() {
  return h("div", { class: "keyscale" }, "toward improving", h("div", { class: "bar" }), "toward concern", h("span", { class: "faint" }, "· vs. own first-60-day baseline"));
}

// ------------------------------------------------------------------ small multiple line panel
export function linePanel(key, p, { registry, axis = false, hit = false, range = null }) {
  const S = p.series[key];
  const dir = dirOf(p, key);
  const ons = onsets(p);
  const rd = h("div", { class: "rd" });
  const host = h("div");
  const el = h("article", { class: "card panel", "data-key": key },
    h("div", { class: "ph" }, h("div", null, h("b", null, S.label), h("span", { class: "u" }, S.unit), hit ? h("span", { class: "mark tone-ember", style: { marginLeft: "10px" } }, "in a pattern") : null), rd), host);

  const lastRoll = [...S.r].reverse().find((x) => x != null);
  const idle = () => {
    clear(rd);
    if (lastRoll == null) return;
    const dv = lastRoll - S.base.mean, pc = S.base.mean ? (dv / S.base.mean) * 100 : 0;
    const bad = dir && ((dir === "up" && dv > 0) || (dir === "down" && dv < 0)) && Math.abs(pc) >= 8;
    rd.append(`now ${fmt(lastRoll)} · baseline ${fmt(S.base.mean)}`, h("i", { style: { background: bad ? "var(--ember-bg)" : "var(--slate-bg)", color: bad ? "var(--ember)" : "var(--slate)" } }, `${signed(pc, 0)}%`));
  };
  idle();

  let draw;
  const ro = new ResizeObserver(() => { const w = host.clientWidth; if (w > 40) draw?.(w); });
  draw = (W) => {
    clear(host);
    const H = 120, ml = 46, mr = 8, mt = 8, mb = axis ? 22 : 8, n = S.n;
    const vals = S.v.filter((x) => x != null);
    let lo = Math.min(...vals, S.base.lo), hi = Math.max(...vals, S.base.hi);
    if (range) { // widen the axis so the reference range is visible, within reason
      const span = hi - lo || 1;
      if (range[0] != null) lo = Math.min(lo, Math.max(range[0], lo - span * 0.6));
      if (range[1] != null) hi = Math.max(hi, Math.min(range[1], hi + span * 0.6));
    }
    const padv = (hi - lo) * 0.08 || 1; lo -= padv; hi += padv;
    const X = (i) => ml + (i / (n - 1)) * (W - ml - mr);
    const Y = (v) => mt + (1 - (v - lo) / (hi - lo)) * (H - mt - mb);
    const svg = s("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `${S.label} over the year with personal baseline` });
    // y ticks
    for (const t of [lo + padv, (lo + hi) / 2, hi - padv]) {
      svg.append(s("line", { x1: ml, x2: W - mr, y1: Y(t), y2: Y(t), style: { stroke: "var(--line)" } }),
        s("text", { x: ml - 8, y: Y(t) + 4, "text-anchor": "end", style: { fill: "var(--ink-3)", fontSize: "11px", fontFamily: "var(--mono)" } }, fmt(t, hi - lo < 10 ? 1 : 0)));
    }
    // month lines
    const start = parseDate(p.start);
    for (let m = 0; m < 14; m++) {
      const d = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + m, 1));
      const i = (d - start) / DAY;
      if (i <= 0 || i >= n) continue;
      svg.append(s("line", { x1: X(i), x2: X(i), y1: mt, y2: H - mb, style: { stroke: "var(--line)", opacity: ".55" } }));
      if (axis) svg.append(s("text", { x: X(i), y: H - 5, "text-anchor": "middle", style: { fill: "var(--ink-3)", fontSize: "11px" } }, fmtDate(d, "short").split(" ")[1]));
    }
    // general reference range (optional), drawn behind everything else
    if (range) {
      const yTop = Y(range[1] ?? hi), yBot = Y(range[0] ?? lo);
      svg.append(s("rect", { x: ml, y: yTop, width: W - ml - mr, height: Math.max(2, yBot - yTop), style: { fill: "var(--blue)", opacity: ".09" } }),
        s("text", { x: W - mr - 4, y: yTop + 12, "text-anchor": "end", style: { fill: "var(--blue)", fontSize: "11px", fontFamily: "var(--mono)" } }, "usual range"));
    }
    // baseline band
    svg.append(s("rect", { x: X(0), y: Y(S.base.hi), width: X(59) - X(0), height: Math.max(2, Y(S.base.lo) - Y(S.base.hi)), rx: 3, style: { fill: "var(--violet)", opacity: ".16" } }),
      s("line", { x1: X(0), x2: W - mr, y1: Y(S.base.mean), y2: Y(S.base.mean), style: { stroke: "var(--violet)", opacity: ".45", strokeDasharray: "4 5" } }));
    // dots
    const g = s("g", { style: { fill: "var(--violet)", opacity: ".28" } });
    S.v.forEach((v, i) => { if (v != null) g.append(s("circle", { cx: X(i), cy: Y(v), r: 1.7 })); });
    svg.append(g);
    // rolling mean
    let d = "", pen = false;
    S.r.forEach((v, i) => { if (v == null) { pen = false; return; } d += `${pen ? "L" : "M"}${X(i).toFixed(1)} ${Y(v).toFixed(1)}`; pen = true; });
    svg.append(s("path", { d, fill: "none", "stroke-width": 2.4, "stroke-linejoin": "round", "stroke-linecap": "round", style: { stroke: hit ? "var(--ember)" : "var(--violet)" } }));
    // onset
    for (const o of ons) {
      const i = (parseDate(o.date) - start) / DAY;
      if (i >= 0 && i < n) svg.append(s("line", { x1: X(i), x2: X(i), y1: mt, y2: H - mb, "stroke-width": 1.6, style: { stroke: "var(--ember)", strokeDasharray: "5 4" } }));
    }
    // meds
    for (const m of p.meds) {
      if (!m.start) continue;
      const i = (parseDate(m.start) - start) / DAY;
      if (i > 0 && i < n) svg.append(s("path", { d: `M${X(i) - 4} ${H - mb} l4 -7 l4 7z`, style: { fill: "var(--blue)" } }, s("title", null, `${m.name} started ${fmtDate(m.start)}`)));
    }
    // crosshair
    const cl = s("line", { y1: mt, y2: H - mb, style: { stroke: "var(--ink)", opacity: 0 } });
    const cd = s("circle", { r: 4.5, style: { fill: "var(--surface)", stroke: hit ? "var(--ember)" : "var(--violet)", strokeWidth: 2.4, opacity: 0 } });
    svg.append(cl, cd);
    const api = {
      set(i) {
        const v = S.v[i], r = S.r[i];
        cl.setAttribute("x1", X(i)); cl.setAttribute("x2", X(i)); cl.style.opacity = ".3";
        if (r != null) { cd.setAttribute("cx", X(i)); cd.setAttribute("cy", Y(r)); cd.style.opacity = 1; } else cd.style.opacity = 0;
        clear(rd);
        const dv = v == null ? null : v - S.base.mean;
        rd.append(`${fmtDate(addDays(p.start, i), "short")} · ${v == null ? "no reading" : fmt(v)}`, dv == null ? null : h("i", { style: { background: "var(--slate-bg)", color: "var(--slate)" } }, `${signed(dv)} vs baseline`));
      },
      off() { cl.style.opacity = 0; cd.style.opacity = 0; idle(); },
    };
    registry.set(key, api);
    svg.addEventListener("pointermove", (e) => {
      const rect = svg.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * W;
      const i = Math.max(0, Math.min(n - 1, Math.round(((x - ml) / (W - ml - mr)) * (n - 1))));
      registry.forEach((a) => a.set(i));
    });
    svg.addEventListener("pointerleave", () => registry.forEach((a) => a.off()));
    host.append(svg);
  };
  // observe after insertion so clientWidth is real
  requestAnimationFrame(() => ro.observe(host));
  return el;
}

// ------------------------------------------------------------------ labs
function parseRef(ref) {
  const r = String(ref || "");
  let m = r.match(/([\d.]+)\s*[–-]\s*([\d.]+)/);
  if (m) return [parseFloat(m[1]), parseFloat(m[2])];
  m = r.match(/^[<≤]\s*([\d.]+)/); if (m) return [0, parseFloat(m[1])];
  m = r.match(/^[>≥]\s*([\d.]+)/); if (m) return [parseFloat(m[1]), Infinity];
  return null;
}
export function labCard(key, lab, p, { hit }) {
  const pts = lab.points, last = pts[pts.length - 1], first = pts[0];
  const ref = parseRef(lab.ref);
  const outside = ref && (last.v < ref[0] || last.v > ref[1]);
  const W = 300, H = 76, ml = 6, mr = 6, mt = 8, mb = 8;
  const t0 = parseDate(p.start).getTime(), t1 = t0 + 364 * DAY;
  const vs = pts.map((x) => x.v).concat(ref ? [ref[0], Number.isFinite(ref[1]) ? ref[1] : ref[0] * 1.3] : []);
  let lo = Math.min(...vs), hi = Math.max(...vs); const pad = (hi - lo) * 0.15 || 1; lo -= pad; hi += pad;
  const X = (d) => ml + ((parseDate(d).getTime() - t0) / (t1 - t0)) * (W - ml - mr);
  const Y = (v) => mt + (1 - (v - lo) / (hi - lo)) * (H - mt - mb);
  const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `${lab.label} results` });
  if (ref) {
    const y1 = Y(Number.isFinite(ref[1]) ? ref[1] : hi), y2 = Y(ref[0]);
    svg.append(s("rect", { x: ml, y: y1, width: W - ml - mr, height: Math.max(2, y2 - y1), rx: 4, style: { fill: "var(--teal)", opacity: ".12" } }));
  }
  svg.append(s("path", { d: pts.map((x, i) => `${i ? "L" : "M"}${X(x.d).toFixed(1)} ${Y(x.v).toFixed(1)}`).join(""), fill: "none", "stroke-width": 2, style: { stroke: hit ? "var(--ember)" : "var(--violet)" } }));
  pts.forEach((x) => {
    const c = s("circle", { cx: X(x.d), cy: Y(x.v), r: 4.2, style: { fill: "var(--surface)", stroke: hit ? "var(--ember)" : "var(--violet)", strokeWidth: 2.2 } });
    c.addEventListener("pointerenter", (e) => tip.show(h("div", null, h("b", null, lab.label), h("div", null, `${fmt(x.v, 2)} ${lab.unit}`), h("div", { style: { opacity: .7 } }, fmtDate(x.d))), e.clientX, e.clientY));
    c.addEventListener("pointerleave", tip.hide);
    svg.append(c);
  });
  const dv = last.v - first.v;
  return h("article", { class: "card lab" },
    h("div", { class: "lh" }, h("b", null, lab.label), outside ? h("span", { class: "mark tone-ember" }, last.v > ref[1] ? "above range" : "below range") : ref ? h("span", { class: "mark tone-teal" }, "in range") : null),
    h("div", { class: "big" }, fmt(last.v, 2), h("small", null, lab.unit)),
    h("div", { class: "d" }, pts.length > 1 ? `${signed(dv, 2)} since ${fmtDate(first.d, "short")} · ${pts.length} results · ref ${lab.ref}` : `1 result · ref ${lab.ref}`),
    svg);
}

export { icon };
