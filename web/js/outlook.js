// Outlook: three short blocks. (1) Your health risks, (2) things to keep an eye on, each with its own trend line, (3) what to do with it.
// Everything else (inputs, method, caveats) sits behind a click, so the page stays calm.
import { h, s, fmt, fmtDate, parseDate, pct, tip, DAY } from "./ui.js";
import { pagehead } from "./record.js";

const TONE = { low: "teal", borderline: "gold", intermediate: "ember", high: "ember", "slightly raised": "gold", moderate: "gold", "very high": "ember" };
const FLAG_TONE = { within: "teal", watch: "gold", outside: "ember" };
const ARROW = { rising: "↗", falling: "↘", steady: "→" };
const GROUP_TONE = { raise: "ember", watch: "gold", data: "teal", habits: "slate" };
const ask = (q) => document.dispatchEvent(new CustomEvent("prana:ask", { detail: q }));

// ---------------------------------------------------------------- risks
function drivers(list, unit, max) {
  const top = Math.max(0.1, ...list.map((d) => d.points));
  return h("div", { class: "drv" }, list.slice(0, max).map((d) => h("div", { class: "dr" },
    h("div", { class: "dl" }, h("b", null, d.label), h("span", null, d.text)),
    h("div", { class: "bar" }, h("i", { style: { width: `${Math.max(8, d.points / top * 100)}%` } })), h("span", { class: "pt" }, `+${d.points} ${unit}`))));
}

function heartCard(p) {
  const r = p.outlook.risk;
  if (!r) return null;
  if (!r.available) {
    return h("article", { class: "risk card" }, h("span", { class: "gk" }, "Heart attack or stroke, next 10 years"), h("b", { class: "rbig muted" }, "Not scored"), h("p", { class: "rline" }, r.reason),
      h("p", { class: "fine" }, "We only show a number where the published formula applies."));
  }
  const ups = r.drivers.filter((d) => !d.fixed);
  return h("article", { class: `risk card tone-${TONE[r.band]}` },
    h("span", { class: "gk" }, "Heart attack or stroke, next 10 years"),
    h("b", { class: "rbig" }, `${r.per100} in 100`), h("span", { class: `mark tone-${TONE[r.band]}` }, `${r.band} band`),
    h("p", { class: "rline" }, ups.length ? `Mostly from ${ups.slice(0, 2).map((d) => d.label.toLowerCase()).join(" and ")}.` : "None of the changeable factors is above its healthy level."),
    h("details", { class: "why" }, h("summary", null, "Why this number"),
      ups.length ? drivers(ups, "pts", 4) : null,
      h("p", { class: "fine" }, "Each bar is how many percentage points the estimate would drop if that one factor were healthy. Age and sex cannot be changed."),
      h("table", { class: "inputs" }, h("tbody", null, r.inputs.map((i) => h("tr", null, h("td", null, i.label), h("td", null, i.value), h("td", { class: "faint" }, i.source))))),
      h("ul", { class: "bullets" }, r.assumptions.map((a) => h("li", null, a))),
      h("p", { class: "fine" }, `${r.bands} ${r.method}. ${r.caveat}`)),
    h("button", { class: "ask-inline", type: "button", onclick: () => ask("What is my chance of a heart attack?") }, "Ask Prana about this →"));
}

function diabetesCard(p) {
  const r = p.outlook.diabetes;
  if (!r) return null;
  if (!r.available) {
    return h("article", { class: "risk card" }, h("span", { class: "gk" }, "Type 2 diabetes, next 10 years"), h("b", { class: "rbig muted" }, "Not scored"), h("p", { class: "rline" }, r.reason));
  }
  const range = r.per100_min === r.per100_max ? `${r.per100_min} in 100` : `${r.per100_min}–${r.per100_max} in 100`;
  const band = r.band_min === r.band_max ? r.band_min : `${r.band_min} to ${r.band_max}`;
  return h("article", { class: `risk card tone-${TONE[r.band_max]}` },
    h("span", { class: "gk" }, "Type 2 diabetes, next 10 years"),
    h("b", { class: "rbig" }, range), h("span", { class: `mark tone-${TONE[r.band_max]}` }, `${band} band`),
    h("p", { class: "rline" }, `Mostly from ${r.drivers.slice(0, 2).map((d) => d.label.toLowerCase()).join(" and ")}.`),
    h("details", { class: "why" }, h("summary", null, "Why this number"),
      drivers(r.drivers, "pts", 5),
      h("p", { class: "fine" }, `Screening score ${r.score_min}${r.score_min === r.score_max ? "" : `–${r.score_max}`}. ${r.assumptions.join(" ")}`),
      h("p", { class: "fine" }, `${r.bands} ${r.method}. ${r.caveat}`)),
    h("button", { class: "ask-inline", type: "button", onclick: () => ask("What is my chance of developing diabetes?") }, "Ask Prana about this →"));
}

// ---------------------------------------------------------------- watch list: a trend line for each measure outside its usual range
function trendChart(w) {
  const pts = w.points.map((x) => ({ t: parseDate(x.d).getTime(), v: x.v }));
  const W = 440, H = 110, ml = 6, mr = 6, mt = 8, mb = 18;
  const last = pts[pts.length - 1], end = w.projection ? last.t + w.projection.days * DAY : last.t, t0 = pts[0].t;
  const vals = [...pts.map((x) => x.v), ...(w.projection ? [w.projection.low, w.projection.high] : [])];
  let lo = Math.min(...vals), hi = Math.max(...vals);
  const pad = (hi - lo || Math.abs(hi) * 0.05 || 1) * 0.15; lo -= pad; hi += pad;
  const X = (t) => ml + ((t - t0) / ((end - t0) || 1)) * (W - ml - mr), Y = (v) => mt + (1 - (v - lo) / (hi - lo)) * (H - mt - mb);
  const f = (t, v) => `${X(t).toFixed(1)},${Y(v).toFixed(1)}`;
  const el = s("svg", { viewBox: `0 0 ${W} ${H}`, class: "fcchart", role: "img", "aria-label": `${w.label} over time` },
    w.projection ? s("path", { d: `M${f(last.t, last.v)} L${f(end, w.projection.high)} L${f(end, w.projection.low)} Z`, class: "band" }) : null,
    s("path", { d: pts.map((x, i) => `${i ? "L" : "M"}${f(x.t, x.v)}`).join(" "), class: "hist", pathLength: 1 }),
    w.projection ? s("path", { d: `M${f(last.t, last.v)} L${f(end, w.projection.value)}`, class: "proj" }) : null,
    pts.length <= 8 ? pts.map((x, i) => s("circle", { cx: X(x.t), cy: Y(x.v), r: 3.2, class: "pdot", style: { "--i": i } })) : null,
    s("circle", { cx: X(last.t), cy: Y(last.v), r: 4, class: "live" }), s("circle", { cx: X(last.t), cy: Y(last.v), r: 4, class: "live ping" }),
    s("circle", { r: 4.5, class: "dot" }),
    s("text", { x: ml, y: H - 4, class: "ax" }, fmtDate(new Date(t0), "short")),
    s("text", { x: W - mr, y: H - 4, class: "ax", "text-anchor": "end" }, fmtDate(new Date(end), "short")));
  const dot = el.querySelector("circle.dot");
  el.addEventListener("pointermove", (e) => {
    const r = el.getBoundingClientRect(), x = ((e.clientX - r.left) / r.width) * W;
    const near = pts.reduce((a, b) => (Math.abs(X(b.t) - x) < Math.abs(X(a.t) - x) ? b : a));
    dot.setAttribute("cx", X(near.t)); dot.setAttribute("cy", Y(near.v)); el.classList.add("hov");
    tip.show(h("div", { class: "ttip" }, h("b", null, `${fmt(near.v, 2)} ${w.unit}`), h("div", null, fmtDate(new Date(near.t)))), e.clientX, e.clientY);
  });
  el.addEventListener("pointerleave", () => { el.classList.remove("hov"); tip.hide(); });
  return el;
}

function watchCard(w) {
  return h("article", { class: "card watch" },
    h("div", { class: "wh" }, h("b", null, w.label), h("span", { class: `mark tone-${FLAG_TONE[w.flag]}` }, w.category)),
    h("p", { class: "wv" }, /^\d+(\.\d+)?$/.test(w.value_text) ? h("span", { "data-count": w.value_text, "data-nd": (w.value_text.split(".")[1] || "").length }, w.value_text) : h("span", null, w.value_text), h("small", null, ` ${w.unit}`), h("span", { class: `dir dir-${w.direction}` }, h("i", { class: "arr" }, ARROW[w.direction]), ` ${w.direction}`)),
    trendChart(w),
    h("p", { class: "fine" }, `${w.change}. ${w.reference_text}.`),
    w.projection ? h("p", { class: "wproj" }, `In about 3 months it may be around ${fmt(w.projection.value)} (likely ${fmt(w.projection.low)} to ${fmt(w.projection.high)}).`)
      : h("p", { class: "fine" }, w.note),
    w.drivers ? h("details", { class: "why" }, h("summary", null, "What drove this?"), h("ul", { class: "bullets" }, w.drivers.map((d) => h("li", null, d)))) : null);
}

function watchSection(p) {
  const W = p.outlook.watch, fc = p.outlook.forecast, ev = fc.evidence && fc.evidence.daily;
  const trust = ev && ev.n ? `Projections appear only when a trend is strong and lasting. In tests on ${fc.evidence.patients} other patients they beat “nothing changes” in ${pct(ev.better_than_nothing_changes)} of ${ev.n} cases, and the real value stayed inside the range ${pct(ev.inside_95_range)} of the time. That is a test on practice data, not a clinical trial. Lab results are not projected because there are too few of them.` : "";
  return h("section", { class: "outlook-sec" },
    h("h2", null, "Things to keep an eye on"),
    h("p", { class: "standfirst" }, W.items.length ? "Each measure that sits outside its usual range, and how it has been moving." : "Everything we track sits within its usual range."),
    h("div", { class: "fcgrid" }, W.items.map(watchCard)),
    W.more.length ? h("p", { class: "fine" }, `Also outside their usual range: ${W.more.join(", ")}. Ask Prana about any of them.`) : null,
    h("details", { class: "why" }, h("summary", null, "How reliable is this?"), h("p", { class: "fine" }, trust || "Projections appear only when a trend is strong and lasting.")));
}

// ---------------------------------------------------------------- suggestions
function recSection(p) {
  const r = p.outlook.recommendations;
  return h("section", { class: "outlook-sec" },
    h("h2", null, "What to do with this"),
    h("p", { class: "standfirst" }, r.summary),
    r.groups.map((g) => h("div", { class: "recgroup" },
      h("h3", { class: `mark tone-${GROUP_TONE[g.id]}` }, g.title),
      g.items.map((i) => h("details", { class: "rec" },
        h("summary", null, i.title),
        h("p", null, i.why.join(" ")),
        i.ask ? h("p", { class: "ask" }, i.ask) : null,
        h("p", { class: "src" }, i.source ? `Source: ${i.source}. ` : "", h("a", { href: i.link }, "See it in your record")))))),
    h("p", { class: "fine" }, r.disclaimer));
}

export function outlookView(p) {
  return h("div", { class: "page" },
    pagehead("Outlook", "A simple look ahead from your own record. Not a diagnosis."),
    h("section", { class: "outlook-sec" }, h("h2", null, "Your health risks"),
      h("p", { class: "standfirst" }, "Estimates from published scores, for groups of people with your readings."),
      h("div", { class: "riskgrid" }, heartCard(p), diabetesCard(p)),
      h("p", { class: "fine" }, "We can’t estimate other conditions. Prana can show where blood pressure, cholesterol, kidney function and weight are heading.")),
    watchSection(p), recSection(p));
}
