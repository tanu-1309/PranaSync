// The clinical view: the deep data behind every plain-language screen, for a doctor. Numbers and tables, with the statistical findings, the risk model's workings,
// every lab result, the documents with their original and corrected values, medicines with adherence, and data quality. Read-only except where a page says so.
import { h, api, fmt, fmtDate, pct } from "./ui.js";
import { hub } from "./hubs.js";
import { historyAsync } from "./homeparts.js";
import { statisticsView, qualityView } from "./record.js";

export const CLINICAL_TABS = [["statistics", "Statistical findings"], ["values", "Values and tables"], ["risk", "Risk model detail"], ["documents", "Documents and extracted values"], ["medicines", "Medicines and adherence"], ["quality", "Data quality"]];
const UPLOAD_TABS = [["risk", "Risk model detail"], ["documents", "Documents and extracted values"]];
const AREA = { heart: "Heart and circulation", diabetes: "Blood sugar (diabetes)", blood_pressure: "Blood pressure" };
const dash = "—";
const when = (iso) => { try { return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }); } catch { return iso || dash; } };
const num = (x, nd = 2) => (x == null || Number.isNaN(x) ? dash : fmt(x, nd));

function tbl(caption, heads, rows, { numeric = [] } = {}) {
  return h("div", { class: "tscroll" }, h("table", { class: "mt ct-table" }, h("caption", null, caption),
    h("thead", null, h("tr", null, heads.map((t, i) => h("th", { scope: "col", class: numeric.includes(i) ? "mt-num" : "" }, t)))),
    h("tbody", null, rows.map((r) => h("tr", null, r.map((c, i) => (i === 0 ? h("th", { scope: "row" }, c) : h("td", { class: numeric.includes(i) ? "mt-num" : "" }, c))))))));
}
const section = (id, title, lead, ...kids) => h("section", { class: "cv-sec", "aria-labelledby": id }, h("h2", { id }, title), lead ? h("p", { class: "tab-lead" }, lead) : null, ...kids);

// ------------------------------------------------------------------ values and tables
async function valuesTab(me) {
  let d;
  try { d = await api("analytics"); } catch { return h("p", { class: "note" }, "The analysis could not be loaded. Please try again."); }
  const labs = Object.values(me.labs || {});
  return h("div", { class: "cv" }, historyAsync(),
    section("cv-base", "Each measurement against the person's own baseline", "Mean of the first 60 days (or first results) against the recent mean. Change and effect size are in the measure's own units.",
      tbl("Baseline comparison", ["Measure", "Area", "Baseline mean", "Recent mean", "Change", "Change %", "Effect size (SD)", "Minimum meaningful change", "Status"],
        d.baseline.map((r) => [r.label, r.area, num(r.baseline_mean), num(r.recent_mean), num(r.change), r.change_pct != null ? `${num(r.change_pct, 1)}%` : dash, num(r.effect_size), num(r.min_change), r.status]), { numeric: [2, 3, 4, 5, 6, 7] })),
    section("cv-trend", "Trend tests", "Mann-Kendall test on weekly means. A trend counts when p is below the threshold.",
      tbl("Trend tests", ["Measure", "Observations", "Coverage", "Weekly points", "Trend", "p-value", "Slope per month", "Period"],
        d.trend.map((r) => [r.label, r.n_observations, r.coverage != null ? pct(r.coverage) : dash, r.weekly_points, r.trend, num(r.p_value, 4), num(r.slope_per_month), r.period ? `${fmtDate(r.period[0])} to ${fmtDate(r.period[1])}` : dash]), { numeric: [1, 2, 3, 5, 6] })),
    section("cv-ref", "Where each level sits against published reference ranges", "Reference bands and their sources. A level can be steady for the person and still outside the usual range.",
      tbl("Reference range comparison", ["Measure", "Latest", "Unit", "Usual range", "Class", "Compared with own usual", "Source", "Measured"],
        d.reference.items.map((r) => [r.label, r.value_text, r.unit || dash, r.reference_text || dash, r.category, (r.change || "not tracked").replace(/_/g, " "), r.source || dash, r.as_of || dash]), { numeric: [1] })),
    section("cv-labs", "Every laboratory result", "All stored results, oldest to newest.",
      labs.length ? tbl("Laboratory results", ["Test", "Unit", "Usual range", "Results", "First", "Latest", "Dates"],
        labs.map((l) => [l.label, l.unit || dash, l.ref || dash, l.points.length, num(l.points[0]?.v), num(l.points[l.points.length - 1]?.v), l.points.map((p) => `${fmtDate(p.d, "med")}: ${num(p.v)}`).join("; ")]), { numeric: [3, 4, 5] })
        : h("p", { class: "note" }, "No laboratory results are stored.")),
    d.forecast.items.length ? section("cv-fc", "Short projections", "Shown only when the trend is very strong. Ranges are 95% ranges.",
      tbl("Projections", ["Measure", "Now", "Trend", "Gate", "30 days", "90 days"], d.forecast.items.map((i) => {
        const at = (days) => { const x = (i.projection || []).find((q) => q.days === days); return x ? `${num(x.value)} (${num(x.low, 1)} to ${num(x.high, 1)})` : dash; };
        return [i.label, num(i.now), i.trend || dash, i.gate_passed ? "passed" : "not met", at(30), at(90)];
      }), { numeric: [1] })) : null);
}

// ------------------------------------------------------------------ risk model detail
async function riskTab() {
  let r, m = null;
  try { [r, m] = await Promise.all([api("clinical/risk", { fresh: true }), api("models").catch(() => null)]); } catch { return h("p", { class: "note" }, "The risk detail could not be loaded."); }
  if (!r.available) return h("p", { class: "note" }, r.reason || "The risk model is not available.");
  const dc = m?.risk?.development_check;
  return h("div", { class: "cv" },
    h("p", { class: "tab-lead" }, "Every value the model used, where it came from, and each value's share of the push on each area. The model's score is never shown: the training data has no follow-up outcomes, so it would claim more than it can support."),
    ...r.areas.map((a) => section(`cv-r-${a.area}`, `${AREA[a.area] || a.label}: ${a.level_text}`, `Evidence ${a.evidence}/100 (${a.evidence_text}). ${a.available ? "" : "Too little information for a class."}${dc ? ` Development check on practice records, all values present: AUC ${dc[a.area]?.complete?.toFixed(2)}.` : ""}`,
      a.rows.length ? tbl(`${AREA[a.area]}: values used`, ["Parameter", "Value", "From", "Push", "Strength", "Share of push", "Model attention", "Rule"],
        a.rows.map((x) => [x.label, x.value, x.from || dash, x.direction === "raises" ? "▲ raises" : x.direction === "lowers" ? "▼ lowers" : "neutral", x.strength, `${x.share}%`, `${x.attention}%`, x.monotone]), { numeric: [5, 6] }) : null,
      a.missing.length ? h("p", { class: "cv-miss" }, h("b", null, "Not available (share of the model's attention): "), a.missing.map((x) => `${x.label} ${x.attention}%`).join(", ")) : null)),
    h("p", { class: "fine" }, r.note, " The class cut-offs were fixed when the model was trained. No clinician has reviewed the parameters, directions or wording."));
}

// ------------------------------------------------------------------ documents and extracted values
async function documentsTab() {
  let r;
  try { r = await api("clinical/documents", { fresh: true }); } catch { return h("p", { class: "note" }, "The documents could not be loaded."); }
  if (!r.documents.length) return h("p", { class: "note" }, "No documents have been uploaded. Values from uploads, with the line each came from, appear here.");
  return h("div", { class: "cv" }, h("p", { class: "tab-lead" }, "Each uploaded document as stored: when it was uploaded, when its text was read, whether it was checked, every value with its original reading and any correction, and the history of changes."),
    ...r.documents.map((d, i) => section(`cv-d-${i}`, d.source.filename, `${d.source.type.toUpperCase()} · ${Math.round(d.source.size_bytes / 1024) || 1} KB · uploaded ${when(d.uploaded_at)} · text read ${when(d.extracted_at)} · ${d.reviewed_at ? `checked ${when(d.reviewed_at)}` : "not yet checked"} · ${d.text_characters} characters of text · fingerprint ${d.source.sha256.slice(0, 12)}…`,
      tbl("Values read", ["Parameter", "Original reading", "Value in use", "Corrected", "Set aside", "Found in the document as", "Observed on"],
        d.values.map((v) => [v.label, v.original_value === v.value && !v.edited ? v.text : String(v.original_value), v.ignored ? dash : v.text, v.edited ? "yes" : "no", v.ignored ? "yes" : "no", v.source_text || dash, v.observed_on || dash])),
      d.edit_history.length ? h("details", { class: "why" }, h("summary", null, `Changes made by the person (${d.edit_history.length})`), h("ul", { class: "list-x" }, d.edit_history.map((x) => h("li", null, h("b", null, x.label), `: ${x.from} → ${x.to} `, h("small", { class: "faint" }, when(x.at)))))) : null,
      h("a", { class: "btn sm", href: `#/review/${d.doc_id}` }, "Open the review page for this document"))));
}

// ------------------------------------------------------------------ medicines and adherence
function medicinesTab(me) {
  const per = {};
  const name = Object.fromEntries((me.meds || []).map((m) => [m.id, m.name]));
  (me.adherence || []).forEach((a) => { (per[a.med] ||= []).push(a); });
  return h("div", { class: "cv" },
    section("cv-meds", "Medicines on record", "Every entry, including doses that changed.",
      (me.meds || []).length ? tbl("Medicines", ["Medicine", "Dose", "Frequency", "For", "Status", "Started", "Stopped", "Reason for change", "Tolerance"],
        me.meds.map((m) => [m.name, m.dose, m.freq, m.for || dash, m.status, m.start ? fmtDate(m.start) : dash, m.end ? fmtDate(m.end) : dash, m.why || dash, m.tolerance || dash])) : h("p", { class: "note" }, "No medicines are on record.")),
    section("cv-adh", "Adherence", "Percent of doses taken, by source (refill estimate or self-report).",
      Object.keys(per).length ? tbl("Adherence by medicine", ["Medicine", "Records", "Average taken", "Lowest", "Latest", "Source"],
        Object.entries(per).map(([id, rows]) => { const v = rows.map((x) => x.pct); return [name[id] || id, rows.length, `${Math.round(v.reduce((a, b) => a + b, 0) / v.length)}%`, `${Math.min(...v)}%`, `${rows[rows.length - 1].pct}% (${fmtDate(rows[rows.length - 1].d)})`, [...new Set(rows.map((x) => x.src))].join(", ")]; }), { numeric: [1, 2, 3, 4] })
        : h("p", { class: "note" }, "No adherence records.")));
}

export function clinicalView(me, sub) {
  const upload = me.mode === "uploads";
  const items = upload ? UPLOAD_TABS : CLINICAL_TABS;
  const render = (k) => ({ statistics: () => statisticsView(me, "clinician"), values: () => valuesTab(me), risk: () => riskTab(), documents: () => documentsTab(), medicines: () => medicinesTab(me), quality: () => qualityView(me) }[k]());
  const side = h("aside", { class: "hub-side", "aria-label": "Clinical view tools" }, h("button", { class: "btn", type: "button", onclick: () => window.print() }, "Print for the clinic"),
    h("small", null, "Prints the tab you are on, with every section open."));
  return hub({ title: "Clinical view", lead: "The deep data behind every plain-language screen, for a doctor: statistical findings, the risk model's workings, every lab result, documents with original and corrected values, medicines and data quality.",
    base: "clinical", items, sub, render, side, aria: "Clinical view sections" });
}
