// Outlook: three short blocks. (1) Your health risks, (2) things to keep an eye on, each with its own trend line, (3) what to do with it.
// Everything else (inputs, method, caveats) sits behind a click, so the page stays calm.
import { h, s, fmt, fmtDate, parseDate, pct, tip, DAY } from "./ui.js";
import { pagehead } from "./record.js";
import { aiReady, aiNotice, aiBadge, shimmer } from "./ai.js";
import { outlookRisk } from "./risk.js";

const FLAG_TONE = { within: "teal", watch: "gold", outside: "ember" };
const ARROW = { rising: "↗", falling: "↘", steady: "→" };
const GROUP_TONE = { raise: "ember", watch: "gold", data: "teal", habits: "slate" };
const ask = (q) => document.dispatchEvent(new CustomEvent("prana:ask", { detail: q }));

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

function watchCard(w, p) {
  return h("article", { class: "card watch" },
    h("div", { class: "wh" }, h("b", null, w.label), h("span", { class: `mark tone-${FLAG_TONE[w.flag]}` }, w.category)),
    h("p", { class: "wv" }, /^\d+(\.\d+)?$/.test(w.value_text) ? h("span", { "data-count": w.value_text, "data-nd": (w.value_text.split(".")[1] || "").length }, w.value_text) : h("span", null, w.value_text), h("small", null, ` ${w.unit}`), h("span", { class: `dir dir-${w.direction}` }, h("i", { class: "arr" }, ARROW[w.direction]), ` ${w.direction}`)),
    trendChart(w),
    h("p", { class: "fine" }, `${w.change}. ${w.reference_text}.`),
    aiReady(p) ? h("p", { class: "wproj" }, p.ai.watch?.[w.label] || "") : shimmer(2));
}

function watchSection(p) {
  const W = p.outlook.watch, fc = p.outlook.forecast, ev = fc.evidence && fc.evidence.daily;
  const trust = ev && ev.n ? `Projections appear only when a trend is strong and lasting. In tests on ${fc.evidence.patients} other patients they beat “nothing changes” in ${pct(ev.better_than_nothing_changes)} of ${ev.n} cases, and the real value stayed inside the range ${pct(ev.inside_95_range)} of the time. That is a test on practice data, not a clinical trial. Lab results are not projected because there are too few of them.` : "";
  return h("section", { class: "outlook-sec" },
    h("h2", null, "Things to keep an eye on"),
    h("p", { class: "standfirst" }, W.items.length ? "Each measure that sits outside its usual range, and how it has been moving." : "Everything we track sits within its usual range."),
    h("div", { class: "fcgrid" }, W.items.map((w) => watchCard(w, p))),
    W.more.length ? h("p", { class: "fine" }, `Also outside their usual range: ${W.more.join(", ")}. Ask Prana about any of them.`) : null,
    h("details", { class: "why" }, h("summary", null, "How reliable is this?"), h("p", { class: "fine" }, trust || "Projections appear only when a trend is strong and lasting.")));
}

// ---------------------------------------------------------------- suggestions
function recSection(p) {
  if (!aiReady(p)) return h("section", { class: "outlook-sec" }, h("h2", null, "What to do with this"), shimmer(3));
  const list = p.ai.suggestions || [];
  const groups = ["raise", "watch", "data", "habits"].map((g) => [g, list.filter((x) => x.group === g)]).filter(([, l]) => l.length);
  return h("section", { class: "outlook-sec" },
    h("div", { class: "aihead" }, h("h2", null, "What to do with this"), aiBadge(p)),
    p.ai.outlook ? h("p", { class: "standfirst" }, p.ai.outlook) : null,
    groups.map(([g, l]) => h("div", { class: "recgroup" },
      h("h3", { class: `mark tone-${GROUP_TONE[g]}` }, { raise: "Worth raising with your care team", watch: "Worth keeping an eye on", data: "Information that would help", habits: "General guidance, if it fits you" }[g]),
      l.map((i) => h("details", { class: "rec" }, h("summary", null, i.title), h("p", null, i.why), i.ask ? h("p", { class: "ask" }, i.ask) : null)))),
    (p.ai.questions_for_doctor || []).length ? h("div", { class: "recgroup" }, h("h3", { class: "mark tone-slate" }, "Questions for your next visit"), h("ul", { class: "bullets" }, p.ai.questions_for_doctor.map((q) => h("li", null, q)))) : null,
    h("p", { class: "fine" }, "Written by an AI model from your record. These are suggestions for a conversation with your care team, not medical advice, and they never mean changing how you take a medicine."));
}

export function outlookView(p) {
  return h("div", { class: "page" },
    pagehead("Outlook", "A simple look ahead from your own record. Not a diagnosis."),
    aiNotice(p, () => document.dispatchEvent(new CustomEvent("prana:retry-ai"))),
    outlookRisk(),
    watchSection(p), recSection(p));
}
