// Analytics & Intelligence: one page that shows how the analysis works and what each AI model said about it.
// The statistics come first and are computed by code (no AI). The two model panels, the comparison and the report load afterwards and say who wrote what.
// No number on this page is made up: every value comes from /api/analytics, which reads the analysis's own results.
import { hl, highlightKey } from "./highlight.js";
import { h, s, api, fmt, fmtDate, parseDate, skeleton } from "./ui.js";
import { pagehead } from "./record.js";
import { convergence, linePanel, labCard, patternSignals } from "./charts.js";

function ensureStyles() {
  if (document.getElementById("analytics-css")) return;
  document.head.append(h("link", { id: "analytics-css", rel: "stylesheet", href: "/assets/css/analytics.css" }));
}

const dash = "—";
const areaOf = (a) => String(a || "").split(" / ")[0];
const v = (x, unit, nd = 2) => (x == null || x === "" ? dash : `${typeof x === "number" ? fmt(x, nd) : x}${unit ? ` ${unit}` : ""}`);
const period = (a) => (a ? `${fmtDate(a[0])} to ${fmtDate(a[1])}` : dash);
const STATE_TONE = { changed: "ember", improving: "teal", stable: "slate", insufficient_data: "faint" };
const STATE_WORD = { changed: "Changed", improving: "Improving", stable: "Stable", insufficient_data: "Not enough data" };
const tone = (st) => h("span", { class: `mark tone-${STATE_TONE[st] || "slate"}` }, STATE_WORD[st] || st || dash);

function table(head, rows, empty) {
  if (!rows.length) return h("p", { class: "an-empty" }, empty || "Nothing to show.");
  return h("div", { class: "an-scroll" }, h("table", { class: "an-table" }, h("thead", null, h("tr", null, head.map((t) => h("th", { scope: "col" }, t)))),
    h("tbody", null, rows.map((r) => h("tr", null, r.map((c, i) => (i === 0 ? h("th", { scope: "row" }, c) : h("td", null, c))))))));
}
const block = (title, sub, ...kids) => h("details", { class: "an-block" }, h("summary", null, h("b", null, title), sub ? h("span", { class: "an-sub" }, sub) : null), h("div", { class: "an-inner" }, ...kids));
const section = (id, num, title, lead, ...kids) => h("section", { class: "an-sec", id: `an-${id}` }, h("header", null, h("span", { class: "an-num" }, num), h("h2", null, title), lead ? h("p", null, lead) : null), ...kids);

// ---------------------------------------------------------------- small SVG charts (units are never mixed: one chart per measurement)
function scale(min, max, a, b) { const span = max - min || 1; return (x) => a + ((x - min) / span) * (b - a); }

function timeChart({ series, band, vlines = [], hlines = [], unit, label, w = 720, ht = 300 }) {
  const pad = { l: 62, r: 16, t: 16, b: 34 };
  const pts = series.flatMap((x) => x.pts.filter((q) => q.v != null));
  const ys = [...pts.map((q) => q.v), ...(band || []).flatMap((q) => [q.lo, q.hi]), ...hlines.map((q) => q.y)];
  const ts = [...pts.map((q) => q.t), ...(band || []).map((q) => q.t), ...vlines.map((q) => q.t)];
  if (!pts.length) return h("p", { class: "an-empty" }, "No readings to draw.");
  const y0 = Math.min(...ys), y1 = Math.max(...ys), padY = (y1 - y0) * 0.1 || 1, lo = y0 - padY, hi = y1 + padY, nd = hi - lo < 10 ? 1 : 0;
  const X = scale(Math.min(...ts), Math.max(...ts), pad.l, w - pad.r), Y = scale(lo, hi, ht - pad.b, pad.t);
  const path = (list) => list.reduce((d, q, i, arr) => (q.v == null ? d : d + `${i === 0 || arr[i - 1].v == null ? "M" : "L"}${X(q.t).toFixed(1)} ${Y(q.v).toFixed(1)} `), "");
  const tmin = Math.min(...ts), tmax = Math.max(...ts), day = (t) => fmtDate(new Date(t).toISOString().slice(0, 10), "short");
  const ticks = [lo, (lo + hi) / 2, hi];
  return s("svg", { viewBox: `0 0 ${w} ${ht}`, class: "an-chart", role: "img", "aria-label": `${label}: ${unit || ""}` },
    ...ticks.map((v2) => [s("line", { x1: pad.l, x2: w - pad.r, y1: Y(v2), y2: Y(v2), class: "gr" }), s("text", { x: pad.l - 8, y: Y(v2) + 4, class: "tk", "text-anchor": "end" }, fmt(v2, nd))]),
    s("line", { x1: pad.l, y1: ht - pad.b, x2: w - pad.r, y2: ht - pad.b, class: "ax" }), s("line", { x1: pad.l, y1: pad.t, x2: pad.l, y2: ht - pad.b, class: "ax" }),
    s("text", { x: pad.l, y: ht - 8, class: "tk" }, day(tmin)), s("text", { x: w - pad.r, y: ht - 8, class: "tk", "text-anchor": "end" }, day(tmax)),
    band && band.length ? s("path", { class: "band", d: "M" + band.map((q) => `${X(q.t).toFixed(1)} ${Y(q.hi).toFixed(1)}`).join(" L") + " L" + [...band].reverse().map((q) => `${X(q.t).toFixed(1)} ${Y(q.lo).toFixed(1)}`).join(" L") + " Z" }) : null,
    ...hlines.map((q) => [s("line", { x1: X(q.t0 ?? tmin), x2: X(q.t1 ?? tmax), y1: Y(q.y), y2: Y(q.y), class: `hl ${q.cls || ""}` }), s("text", { x: X(q.t1 ?? tmax) - 2, y: Y(q.y) - 6, class: "tk", "text-anchor": "end" }, q.label)]),
    ...series.map((x) => s("path", { d: path(x.pts), class: `ln ${x.cls || ""}`, fill: "none" })),
    ...vlines.map((q) => [s("line", { x1: X(q.t), x2: X(q.t), y1: pad.t, y2: ht - pad.b, class: "vl" }), s("text", { x: X(q.t) + 6, y: pad.t + 12, class: "tk" }, q.label)]));
}

// Horizontal bars, one per measure. The name is never cut short, and each value sits in its own column at the right so it can never run into a label or a bar.
function hbars({ rows, max, threshold, unitLabel, w = 740 }) {
  const rowH = 34, top = 30, left = 280, right = 80, ht = top + rows.length * rowH + 14;
  const hiEnd = Math.max(0, threshold ?? 0, ...rows.map((r) => r.value)) * 1.2 + 0.1, loEnd = Math.min(0, ...rows.map((r) => r.value)) * 1.08 - 0.1, X = scale(loEnd, hiEnd, left + 12, w - right);   // the scale fits the bars, so they are as long as they can be
  return s("svg", { viewBox: `0 0 ${w} ${ht}`, class: "an-chart", role: "img", "aria-label": unitLabel },
    s("line", { x1: X(0), x2: X(0), y1: top - 6, y2: ht - 8, class: "ax" }),
    threshold != null ? [s("line", { x1: X(threshold), x2: X(threshold), y1: top - 6, y2: ht - 8, class: "vl" }), s("text", { x: X(threshold), y: top - 12, class: "tk", "text-anchor": "middle" }, `size rule: ${threshold}`)] : null,
    ...rows.map((r, i) => {
      const y = top + i * rowH, tone = STATE_TONE[r.status] || "slate";
      return [i % 2 ? null : s("rect", { x: 0, y: y - 2, width: w, height: rowH, class: "stripe" }),
        s("text", { x: left, y: y + 21, class: "tk lab", "text-anchor": "end" }, r.label),
        s("rect", { x: Math.min(X(0), X(r.value)), y: y + 6, width: Math.max(2, Math.abs(X(r.value) - X(0))), height: 18, rx: 3, class: `bar tone-${tone}` }),
        s("text", { x: w - 8, y: y + 21, class: "val", "text-anchor": "end" }, fmt(r.value, 2))];
    }));
}

function shareBars(rows, w = 700) {
  const rowH = 32, left = 240, right = 70, ht = rows.length * rowH + 10, X = scale(0, 1, left + 12, w - right);
  return s("svg", { viewBox: `0 0 ${w} ${ht}`, class: "an-chart", role: "img", "aria-label": "Share of days with a reading, for each measurement" },
    ...rows.map((r, i) => {
      const y = i * rowH + 4;
      return [s("text", { x: left, y: y + 18, class: "tk lab", "text-anchor": "end" }, r.label),
        s("rect", { x: left + 12, y: y + 5, width: X(1) - left - 12, height: 16, rx: 3, class: "track" }),
        s("rect", { x: left + 12, y: y + 5, width: Math.max(0, X(r.share ?? 0) - left - 12), height: 16, rx: 3, class: "bar tone-teal" }),
        s("text", { x: w - 8, y: y + 18, class: "val", "text-anchor": "end" }, `${Math.round((r.share ?? 0) * 100)}%`)];
    }));
}

const tsOf = (d) => parseDate(d).getTime();
const seriesPts = (S, field = "v") => S[field].map((x, i) => ({ t: tsOf(S.start) + i * 86400000, v: x }));

// ---------------------------------------------------------------- statistical details
const chipOf = (txt, cls = "slate") => h("span", { class: `mark tone-${cls}` }, txt);
const list = (title, items) => (items && items.length ? h("div", { class: "an-list" }, h("b", { class: "an-h4" }, title), h("ul", null, items.map((t) => h("li", null, typeof t === "string" ? t : JSON.stringify(t))))) : null);

function meta(rows) { return h("dl", { class: "an-meta" }, rows.filter(([, x]) => x != null && x !== "").flatMap(([k, x]) => [h("dt", null, k), h("dd", null, String(x))])); }

function renderMedgemma(r) {
  const m = r.model || {};
  if (r.status === "ok" && r.assessment) {
    const a = r.assessment;
    return h("div", null, meta([["Provider", m.provider], ["Model", m.model_name], ["Version", m.model_version], ["Generated", a.model_metadata?.timestamp], ["Generation time", m.latency_ms == null ? "not recorded" : `${m.latency_ms} ms`],
      ["Validation", "passed: schema, numbers, wording and references checked"], ["Answered by a fallback model", m.fallback_from ? `yes, instead of ${m.fallback_from}` : null], ["Stored result", r.cached ? "yes" : "no"]]),
    h("p", null, chipOf(a.urgency === "requires_clinical_review" ? "Worth a clinical review" : a.urgency === "seek_urgent_care" ? "Seek care promptly" : "Routine discussion", a.urgency === "routine_discussion" ? "teal" : "gold")),
    list("What the record shows", a.analytical_findings), list("Medical-context interpretation", a.medical_interpretations), list("Possible explanations", a.possible_explanations), list("Supporting evidence", a.supporting_evidence),
    list("Contradicting evidence", a.contradicting_evidence), list("Missing clinical information", a.missing_information), list("Recommended next steps", a.recommended_next_steps), list("Uncertainty", a.uncertainty), list("Limitations", a.limitations),
    h("div", { class: "an-list" }, h("b", { class: "an-h4" }, "Medical references"), r.references.length ? h("ul", null, r.references.map((x) => h("li", null, `${x.title} · ${x.source}${x.published ? ` · ${x.published}` : ""}${x.version ? ` · ${x.version}` : ""}`, x.url ? [" ", h("a", { href: x.url, target: "_blank", rel: "noopener noreferrer" }, "Open the source", h("span", { class: "sr" }, ` for ${x.title} (opens in a new tab)`))] : null)))
      : h("p", { class: "an-empty" }, r.retrieval?.note || "No approved reference was cited.")),
    (r.safety?.deterministic || []).map((t) => h("p", { class: "an-note an-warn" }, t)), (r.safety?.adjustments || []).length ? list("Corrections made by the safety rules", r.safety.adjustments) : null,
    h("p", { class: "an-note" }, "Written by an AI model, not clinically validated, and not a diagnosis."));
  }
  const why = { blocked: "Not sent: this record is not approved for the external model.", disabled: "MedGemma is switched off. No endpoint is connected.", not_generated: "Nothing has been generated yet.", error: r.message, safety_reply: r.message };
  return h("div", null, r.model ? meta([["Provider", m.provider], ["Model", m.model_name], ["Status", m.status]]) : null, h("p", { class: "an-empty" }, why[r.status] || r.message || "Not available."));
}

function askBox() {
  const input = h("textarea", { class: "an-ask", rows: 2, maxlength: 500, placeholder: "Ask about your record, for example: what does my blood pressure trend mean?", "aria-label": "Your question" });
  const out = h("div", { class: "an-panel-body" });
  const btn = h("button", { type: "button", class: "cta solid sm an-btn" }, "Ask");
  btn.addEventListener("click", async () => {
    const q = input.value.trim();
    if (!q) return;
    btn.disabled = true; out.replaceChildren(h("p", { class: "an-empty" }, "Working on it…"), skeleton(50));
    try { out.replaceChildren(renderMedgemma(await api("analytics/ask", { method: "POST", body: { question: q } }))); }
    catch (e) { out.replaceChildren(h("p", { class: "an-empty" }, e.status === 429 ? "Please wait a moment and try again." : "The question could not be answered.")); }
    btn.disabled = false;
  });
  return h("div", { class: "an-askbox" }, h("h3", null, "Ask a medical-context question"),
    h("p", { class: "an-note" }, "Emergency, medicine and diagnosis questions always get a fixed, careful reply and never reach a model. Please do not type your name or contact details."), input, h("div", { class: "an-actions" }, btn), out);
}

function comparison(d) {
  const on = d.models.comparison_enabled;
  const body = h("div", { class: "an-panel-body" }, on ? h("p", { class: "an-empty" }, "Press the button to run both models on the same input. It makes two model calls.") : h("p", { class: "an-empty" }, "Comparison mode is switched off (PRANA_MODEL_COMPARISON_ENABLED). Only one model runs per request."));
  const btn = h("button", { type: "button", class: "cta solid sm an-btn", disabled: !on }, "Run comparison");
  btn.addEventListener("click", async () => {
    btn.disabled = true; body.replaceChildren(h("p", { class: "an-empty" }, "Both models are working…"), skeleton(60));
    try {
      const r = await api("analytics/compare", { fresh: true });
      if (r.status !== "ok") { body.replaceChildren(h("p", { class: "an-empty" }, r.message || "Not available.")); }
      else {
        const m = r.metrics, col = (name, x) => h("article", { class: "an-card" }, h("h3", null, name), meta([["Status", x.status], ["Model", x.model_name], ["Version", x.model_version], ["Latency", x.latency_ms == null ? null : `${x.latency_ms} ms`], ["Validation", m.validation[x.provider]]]),
          x.assessment ? list("Interpretation", x.assessment.medical_interpretations) : h("p", { class: "an-empty" }, x.message || "No valid answer."));
        body.replaceChildren(h("div", { class: "an-grid" }, col("NVIDIA Nemotron", r.nemotron), col("Google MedGemma", r.medgemma)),
          h("article", { class: "an-card" }, h("h3", null, "Mechanical comparison"), table(["Check", "Nemotron", "MedGemma"], [["Response time", v(m.latency_ms.nemotron, "ms", 0), v(m.latency_ms.medgemma, "ms", 0)], ["Schema validation", m.validation.nemotron, m.validation.medgemma],
            ["Unsupported claims", m.unsupported_claims_detected.nemotron || "none detected", m.unsupported_claims_detected.medgemma || "none detected"], ...(m.urgency ? [["Urgency", m.urgency.nemotron, m.urgency.medgemma]] : []),
            ...(m.word_overlap != null ? [["Word overlap", String(m.word_overlap), ""]] : [])]),
          m.shared_numbers ? h("p", { class: "an-note" }, `Numbers both used: ${m.shared_numbers.join(", ") || "none"}. Only Nemotron: ${m.numbers_only_in.nemotron.join(", ") || "none"}. Only MedGemma: ${m.numbers_only_in.medgemma.join(", ") || "none"}.`) : null,
          m.missing_information ? list("Missing information only one model listed", [...m.missing_information.only_nemotron.map((t) => `Nemotron: ${t}`), ...m.missing_information.only_medgemma.map((t) => `MedGemma: ${t}`)]) : null,
          list("Possible contradictions (for a person to review)", m.possible_contradictions), h("p", { class: "an-note" }, m.note)));
      }
    } catch (e) { body.replaceChildren(h("p", { class: "an-empty" }, e.status === 429 ? "Please wait a moment and try again." : "The comparison could not run.")); }
    btn.disabled = !on;
  });
  return block("Compare the two models", "side by side, mechanical checks only", h("div", { class: "an-actions" }, btn), body);
}

const by = (name, cls) => h("span", { class: `an-by ${cls}` }, name);

function strip(d) {
  const o = d.overview;
  const items = [["Signal checks analysed", `${o.signals_analysed} of ${o.signals_in_scope}`], ["Changed", o.signals_changed], ["Patterns found", o.patterns_detected], ["Outside range", o.reference_outside],
    ["Data completeness", o.data_completeness == null ? dash : `${Math.round(o.data_completeness * 100)}%`]];
  return h("div", { class: "an-strip" }, items.map(([l, x]) => h("div", null, h("b", null, String(x)), h("span", null, l))));
}

// One card per graph: the graph, how to read it, and a line from Nemotron that fills in after the summary is written.
function graphCards(d) {
  const eff = d.charts.effect_sizes, fc = d.charts.forecast, ref = d.reference.items.filter((r) => r.flag !== "within");
  const specs = [
    { id: "effect", title: "How far each measure moved from your own baseline", how: "Bars are in baseline standard deviations. Positive means moving in the direction of concern. A bar past the dotted line met the size rule.",
      body: eff.length ? hbars({ rows: eff.map((r) => ({ label: `${r.label} · ${areaOf(r.area).split(" ")[0]}`, value: r.effect_size, status: r.status })), max: Math.max(1.2, ...eff.map((r) => Math.abs(r.effect_size))), threshold: d.charts.effect_threshold, unitLabel: "Effect size by measure" }) : h("p", { class: "an-empty" }, "No measure had enough data.") },
    { id: "forecast", title: "Where a trend is heading", how: "Weekly averages (grey), the projection if the trend continues (dashed) and the range it will probably fall in (shaded). Only strong, lasting trends are projected.",
      body: fc.length ? h("div", { class: "an-grid" }, fc.map((c) => {
        const last = c.weekly[c.weekly.length - 1], t0 = tsOf(last[0]), base = tsOf(c.as_of || last[0]), proj = c.projection.map((q) => ({ t: base + q.days * 86400000, ...q }));
        return h("div", null, h("b", { class: "an-h4" }, `${c.label}`), timeChart({ label: c.label, unit: c.unit, series: [{ pts: c.weekly.map(([dd, x]) => ({ t: tsOf(dd), v: x })), cls: "d" }, { pts: [{ t: t0, v: last[1] }, ...proj.map((q) => ({ t: q.t, v: q.value }))], cls: "f" }],
          band: [{ t: t0, lo: last[1], hi: last[1] }, ...proj.map((q) => ({ t: q.t, lo: q.low, hi: q.high }))] }));
      })) : h("p", { class: "an-empty" }, "No measure passed the strict rule for a projection, so none is drawn.") },
    { id: "completeness", title: "How complete the data is", how: "The share of days with a reading. A missing day is never counted as zero.", body: shareBars(d.charts.completeness) },
    { id: "reference", title: "Results outside or near the edge of their usual range", how: "Only results that are not comfortably inside their range are listed.",
      body: ref.length ? h("ul", { class: "an-reflist" }, ref.map((r) => h("li", null, h("span", { class: `mark tone-${r.flag === "outside" ? "ember" : "gold"}` }, r.category || dash), h("b", null, r.label), ` ${v(r.value_text, r.unit)} (usual range ${r.reference_text || dash})`))) : h("p", { class: "an-empty" }, "Every result is comfortably inside its range.") }];
  return specs.map((c) => { const note = h("p", { class: "an-explain" }); return { id: c.id, note, el: h("article", { class: "an-card an-graph" }, h("h3", null, c.title), h("p", { class: "an-note" }, c.how), h("div", { class: "an-gbody" }, h("div", { class: "an-gchart" }, c.body), note)) }; });
}

function summarySection(d) {
  const summaryEl = h("div", { class: "an-panel-body" }, skeleton(60));
  const graphs = graphCards(d);
  const on = d.models.nemotron.enabled;
  const btn = h("button", { type: "button", class: "cta solid sm an-btn", disabled: true }, "Write the summary");
  const fill = (r) => {
    if (r.status === "ok") {
      summaryEl.replaceChildren(h("p", { class: "an-lead" }, r.summary), meta([["Written by", `${r.model.model_name} (NVIDIA Nemotron)`], ["Written", r.generated_at], ["Check", r.validation]]));
      graphs.forEach((g) => g.note.replaceChildren(by("NVIDIA Nemotron", "nem"), " ", r.graphs[g.id]));
      btn.textContent = "Rewrite the summary";
    } else {
      summaryEl.replaceChildren(h("p", { class: "an-empty" }, r.message || "Not available."));
      graphs.forEach((g) => g.note.replaceChildren(h("span", { class: "an-empty" }, "Nemotron's explanation of this graph appears here once the summary is written.")));
    }
  };
  const load = async (cachedOnly) => {
    btn.disabled = true;
    if (!cachedOnly) summaryEl.replaceChildren(h("p", { class: "an-empty" }, "Nemotron is writing. On a free model this can take a few minutes."), skeleton(50));
    try { fill(await api(`analytics/summary${cachedOnly ? "?cached_only=1" : ""}`, { fresh: true })); }
    catch (e) { summaryEl.replaceChildren(h("p", { class: "an-empty" }, e.status === 429 ? "Please wait a moment and try again." : "The summary could not be loaded.")); }
    btn.disabled = !on;
  };
  btn.addEventListener("click", () => load(false));
  load(true);
  return section("summary", "", "Summary and graphs", "Your analysis in plain words, with a short explanation under each graph.",
    h("div", { class: "an-actions" }, by("NVIDIA Nemotron", "nem"), btn, !on ? h("span", { class: "an-note" }, "Nemotron is switched off.") : null), summaryEl, h("div", { class: "an-graphs" }, graphs.map((g) => g.el)));
}

const LEVEL_WORD = { low: "Low", moderate: "Moderate", high: "High" };

function evidenceTable(rows) {
  return table(["Measure", "Latest value", "Usual range", "Your baseline to recent", "Trend (p-value)"],
    rows.map((r) => [r.found ? r.measure : `${r.measure} (no numbers in the analysis)`, r.value || dash, r.reference || dash,
      r.baseline != null ? `${v(r.baseline, r.unit)} to ${v(r.recent, r.unit)} (effect ${v(r.effect_size)})` : dash, r.trend ? `${r.trend} (${v(r.p_value, null, 4)})` : dash]));
}

// One insight, laid out so it can be read in ten seconds: the point in one line, your numbers as chips, how we got there, what it means, and what to do.
function insightCard(i, n) {
  const c = i.confidence;
  const chips = i.evidence.filter((r) => r.found).map((r) => h("li", { class: "in-chip" }, h("span", { class: "in-chip-n" }, r.measure), h("b", null, r.value || dash), r.reference ? h("small", null, `usual: ${r.reference}`) : null));
  return h("article", { class: "an-card an-insight in-card" },
    h("header", { class: "in-head" }, h("span", { class: "in-n", "aria-hidden": "true" }, n), h("h3", null, i.title), h("span", { class: `mark tone-${c.level === "high" ? "teal" : c.level === "moderate" ? "gold" : "slate"}` }, `Model confidence: ${LEVEL_WORD[c.level]}`)),
    hl("p", { class: "in-short" }, i.statement),
    chips.length ? h("ul", { class: "in-chips", "aria-label": "Your numbers for this insight" }, chips) : null,
    h("p", { class: "an-note in-why-conf" }, `${c.reason}${c.capped ? ` The model said ${LEVEL_WORD[c.model_level] || c.model_level}; it was lowered because the statistics do not support more.` : ""}`),
    h("div", { class: "in-grid" },
      h("section", { class: "in-how", "aria-label": "How we got there" }, h("h4", null, "How we got there"), h("ol", null, i.reasoning.map((t) => hl("li", null, t)))),
      h("section", { class: "in-means", "aria-label": "What it means medically" }, h("h4", null, "What it means medically"), hl("p", null, i.medical_context),
        h("p", { class: "an-note" }, "General medical knowledge from the model. Any guideline numbers here come from its memory and are not checked against your record."),
        i.sources.length ? h("ul", { class: "an-sources" }, i.sources.map((x) => h("li", null, h("b", null, x.title), ` · ${x.source}${x.published ? ` · ${x.published}` : ""}${x.version ? ` · ${x.version}` : ""}`, x.url ? [" ", h("a", { href: x.url, target: "_blank", rel: "noopener noreferrer" }, "Open the source", h("span", { class: "sr" }, ` for ${x.title} (opens in a new tab)`))] : null, h("blockquote", null, x.passage.length > 320 ? `${x.passage.slice(0, 320)}…` : x.passage))))
          : h("p", { class: "an-note" }, "No approved medical reference is loaded for this topic, so this explanation is the model's general knowledge, not a cited source."))),
    h("aside", { class: "in-next", "aria-label": "Next step" }, h("b", null, "Next step"), hl("p", null, i.next_step)),
    h("details", { class: "why" }, h("summary", null, "Show the numbers behind this"), h("p", { class: "an-note" }, "From the statistics, not from the AI model:"), evidenceTable(i.evidence)));
}

function renderInsights(r) {
  if (r.status !== "ok") return h("p", { class: "an-empty" }, r.message || "Not available.");
  const m = r.model || {};
  return h("div", { class: "an-panel-body" },
    h("div", { class: "in-overall" }, h("b", null, "The main point"), hl("p", { class: "an-lead" }, r.overall)), highlightKey(), ...r.insights.map((i, k) => insightCard(i, k + 1)),
    list("What is uncertain", r.uncertainty), list("Limits", r.limitations), (r.safety?.adjustments || []).length ? list("Corrections made by the safety rules", r.safety.adjustments) : null,
    meta([["Written by", m.fallback_from ? `${m.model_name} (NVIDIA Nemotron, because ${m.fallback_from} is not connected)` : `${m.model_name} (${m.provider === "medgemma" ? "Google MedGemma" : m.provider})`], ["Version", m.model_version], ["Written", r.generated_at], ["Stored result", r.cached ? "yes" : "no"]]),
    h("p", { class: "an-note" }, `${r.disclaimer} Not clinically validated.`));
}

function insightsSection(d) {
  const mg = d.models.medgemma, nemOn = d.models.nemotron.enabled;
  const out = h("div", { class: "an-panel-body" }, skeleton(70));
  const btn = h("button", { type: "button", class: "cta solid sm an-btn", disabled: true }, "Generate insights");
  const alt = !mg.configured && nemOn ? h("button", { type: "button", class: "cta sm an-btn", disabled: true, title: "MedGemma is not connected, so Nemotron answers instead and the result says so" }, "Generate with Nemotron instead") : null;
  const lock = (on) => { btn.disabled = on || !mg.configured; if (alt) alt.disabled = on; };
  const load = async (cachedOnly, fallback) => {
    lock(true);
    if (!cachedOnly) out.replaceChildren(h("p", { class: "an-empty" }, "The model is reading your data. This can take up to a few minutes."), skeleton(60));
    try { const r = await api(`analytics/insights?${cachedOnly ? "cached_only=1" : ""}${fallback ? "&fallback=1" : ""}`, { fresh: true }); out.replaceChildren(renderInsights(r)); if (r.status === "ok") btn.textContent = "Generate again"; }
    catch (e) { out.replaceChildren(h("p", { class: "an-empty" }, e.status === 429 ? "Please wait a moment and try again." : "The insights could not be loaded.")); }
    lock(false);
  };
  btn.addEventListener("click", () => load(false, false));
  if (alt) alt.addEventListener("click", () => load(false, true));
  load(true, !mg.configured && nemOn);
  const state = mg.configured ? null : h("p", { class: "an-note" }, mg.enabled ? "MedGemma is switched on but no endpoint is set up." : "Google MedGemma is not connected yet (no endpoint). See docs/MEDGEMMA.md.", alt ? " You can see the same feature now with Nemotron answering instead; the result is labelled." : "");
  return section("insights", "", "Medical insights", "A medical model reads your data and says what stands out, what made it say so, and how confident the analysis is.",
    h("div", { class: "an-actions" }, by("Google MedGemma", "med"), btn, alt), state, out, block("Ask a medical question", "about your own record", askBox()));
}

// ---------------------------------------------------------------- the page
// The app re-renders the current page whenever the AI text finishes loading. One page per patient is built once and reused.
let built = { p: null, page: null };
export function analyticsView(p) {
  if (built.p !== p) built = { p, page: build(p) };
  return built.page;
}

async function build(p) {
  ensureStyles();
  const root = h("div", { class: "page analytics" }, pagehead("Analytics & Intelligence", "Two AI models read your analysis. NVIDIA Nemotron explains it and the graphs in plain words. Google MedGemma reads your data for medical insights and shows what led to each one."));
  const body = h("div", { class: "an-body" }, skeleton(120), skeleton(160));
  root.append(body);
  let d;
  try { d = await api("analytics", { fresh: true }); } catch (e) { built = { p: null, page: null }; body.replaceChildren(h("p", { class: "an-empty" }, e.status === 401 ? "Please sign in again." : "The analytics could not be loaded. Please try again in a moment.")); return root; }
  const parts = [strip(d), summarySection(d), insightsSection(d),
    d.models.comparison_enabled ? h("section", { class: "an-sec", id: "an-compare" }, comparison(d)) : null,
    h("aside", { class: "an-more", "aria-label": "Clinical view" }, h("div", null, h("b", null, "The tables behind every number"), h("p", null, "Statistical findings, every lab value, the risk model’s workings and the documents behind them are in the clinical view.")),
      h("a", { class: "btn solid", href: "#/clinical" }, "Open the clinical view")),
    h("p", { class: "fine" }, "This page describes the patient's own data. It does not diagnose and does not advise on medicines. Statistics are calculated by code; AI text is labelled with the model that wrote it. Nothing here has been clinically validated.")];
  body.replaceChildren(...parts.filter(Boolean));              // replaceChildren turns a null into the text "null": leave the empty ones out
  return root;
}
