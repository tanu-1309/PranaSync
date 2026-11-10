import { h, api, pct } from "./ui.js";
import { pagehead } from "./record.js";

const sec = (n, title, text) => h("header", { class: "sec" }, h("span", { class: "sn" }, n), h("h2", null, title), text ? h("p", null, text) : null);

const STEPS = [
  ["01", "Understand", "We read your workbook, clean it, and merge everything onto one dated timeline: vitals, wearables, labs, cycles, history, medications, notes.", "prana.data"],
  ["02", "Connect", "Each change is linked back to your record: prior findings, related medications, family history, earlier labs, tagged before or during the pattern.", "prana.insight.context_linker"],
  ["03", "Detect", "Every signal is compared with your own first 60 days. A pattern surfaces only when several related signals move together.", "prana.analysis"],
  ["04", "Explain", "What changed, by how much, since when, with the exact evidence. Code does the numbers; words only describe them.", "prana.insight.explainer"],
  ["05", "Ask", "We say what is missing and why it matters: a stale HbA1c, a missing hormone panel, a device that stopped syncing.", "prana.insight.missing_data"],
];
const TESTS = [
  ["≥ 60", "days of record", "Enough data: at least half the days present and 20+ baseline days."],
  ["Size", "clinical minimum", "The shift must be big enough to matter: 2 kg, 6 mmHg systolic, 15% of steps."],
  ["0.8 SD", "against your own noise", "The shift must stand clear of how much you normally vary."],
  ["p < .05", "a real trend", "Mann-Kendall test on weekly means, in the direction of concern."],
  ["Still on", "in the last 60 days", "A holiday dip that recovered is not reported."],
];

export function methodView() {
  return h("div", { class: "page" },
    pagehead("A pattern needs company.", "A single high reading is just a high/low alert. We look for several related signals leaving your own normal together, then tie the change to your history and show the evidence."),
    sec("01", "Five steps, end to end"),
    h("div", { class: "steps" }, STEPS.map(([n, t, d, c]) => h("article", { class: "step" }, h("span", { class: "n" }, n), h("h3", null, t), h("p", null, d), h("code", null, c)))),
    sec("02", "Five tests before a signal counts as “changed”", "Each test removes one kind of false alarm: tiny drifts, noisy signals, random wiggles, and dips that recovered."),
    h("div", { class: "tests" }, TESTS.map(([b, t, d]) => h("div", { class: "test" }, h("div", { class: "big" }, b), h("h4", null, t), h("p", null, d)))),
    sec("03", "Then three more conditions make it a pattern"),
    h("ul", { class: "list-x" }, ["At least three signals in the same health area have changed.", "Their change points fall within 150 days of each other (labs are exempt, since they are sparse).", "At least one core signal is among them: blood pressure for hypertension, cycle length or testosterone for PCOS, HbA1c, glucose, weight or steps for metabolic health."].map((t) => h("li", null, t))),
    sec("04", "Two questions, two kinds of reference", "Change detection and reference ranges answer different questions. We report both side by side and never let one hide the other."),
    h("div", { class: "two" },
      h("div", null, h("h3", null, "Your own baseline"), h("ul", { class: "list-x" }, ["Used to find patterns: has this changed for you?", "Compares you with your first 60 days, so what is normal for you stays normal.", "Cannot see a level that was already outside the usual range on day one and never moved."].map((t) => h("li", null, t)))),
      h("div", null, h("h3", null, "General reference ranges"), h("ul", { class: "list-x" }, ["Used to place a level: is it within the usual range?", "Published guideline values (blood pressure, HbA1c, glucose, lipids, heart rate, sleep, BMI, cycle length) plus the range printed on each lab report.", "Never used to decide that something changed, and never worded as a condition. Signals with no meaningful crowd range (HRV, weight, stress) are judged against you only."].map((t) => h("li", null, t))))),
    sec("05", "What this is, and is not"),
    h("div", { class: "two" },
      h("div", null, h("h3", null, "It is"), h("ul", { class: "list-x yes" }, ["A proof-of-concept that adds clinical context to ongoing data, and the reverse.", "Explainable: every insight lists its evidence, its history link and its limits.", "Extensible: the three areas are configuration, so a fourth needs no new model.", "Honest about gaps: it analyses what exists, then asks for what’s missing."].map((t) => h("li", null, t)))),
      h("div", null, h("h3", null, "It is not"), h("ul", { class: "list-x no" }, ["A diagnosis, or a replacement for your clinician.", "A threshold alarm or a black-box risk score.", "Three isolated disease classifiers.", "A production clinical decision system. It is validated on planted patterns, not clinical outcomes."].map((t) => h("li", null, t))))),
    sec("06", "Where the project stands", "Four of ten work packages are done. The rest are planned with PranaChain’s feedback in the loop."),
    h("div", { class: "roadmap" }, Array.from({ length: 10 }, (_, i) => i + 1).map((n) => h("div", { class: `wp ${n <= 4 ? "done" : ""}` }, h("b", null, n), n <= 4 ? "done" : "planned"))),
    h("p", { class: "fine" }, "Next: clinician review of the reference ranges, AI-written suggestions that are checked against the evidence before anyone sees them, real workbooks reviewed with PranaChain, PostgreSQL, adherence-aware baselines, user testing with patients and clinicians, a fourth health area, fairness checks, and handoff."));
}

function pair(label, ours, base, { lowerIsBetter = false } = {}) {
  const worse = lowerIsBetter ? base > ours : base < ours;
  const row = (who, v, cls) => h("div", { class: "hb" }, h("span", { class: "who2" }, who), h("div", { class: "track" }, h("div", { class: `fill ${cls}`, style: { width: "0%" }, "data-w": `${v * 100}%` })), h("span", { class: "vv" }, v.toFixed(2)));
  return h("div", { class: "bar-row" }, h("b", { style: { fontWeight: 500 } }, label), h("div", { class: "pair" }, row("ours", ours, "ours"), row("threshold", base, worse ? "bad" : "base")));
}
const big = ([v, l, s]) => h("div", { class: "bn" }, h("div", { class: "v" }, v), h("div", { class: "l" }, l), h("div", { class: "s" }, s));

export async function evidenceView() {
  const root = h("div", { class: "page" }, pagehead("Quiet when it should be, loud when it matters.", "How we know the pipeline behaves, tested on workbooks where we planted the patterns ourselves."));
  let m;
  try { m = await api("validation"); } catch { root.append(h("p", { class: "muted", style: { marginTop: "24px" } }, "Validation results aren’t available yet.")); return root; }
  const o = m.overall;
  const area = { t2d: "Metabolic", htn: "Cardiovascular", pcos: "Women’s health" };
  root.append(
    h("div", { class: "note", style: { marginTop: "26px", maxWidth: "70ch" } }, h("b", null, `Measured on ${m.n_patients} test workbooks with planted ground truth. `), "Real records carry no answer key, so accuracy can only be measured where we know the answer. These numbers show the pipeline works end to end, not clinical accuracy."),
    sec("01", "Headline numbers"),
    h("div", { class: "bignum" }, [
      [o.ours.precision.toFixed(2), "precision (ours)", `threshold alert ${o.threshold_alert.precision.toFixed(2)}`],
      [o.ours.recall.toFixed(2), "recall (ours)", `threshold alert ${o.threshold_alert.recall.toFixed(2)}`],
      [pct(m.false_alarm_rate_stable_people.ours), "stable people flagged", `threshold alert ${pct(m.false_alarm_rate_stable_people.threshold_alert)}`],
      [pct(m.context_linking_accuracy.accuracy), "history linked correctly", `${m.context_linking_accuracy.n} of ${m.context_linking_accuracy.n} patterns`]].map(big)),
    sec("02", "Where it beats a simple alert, and where it doesn’t"),
    h("div", { class: "two" },
      h("div", null, h("h3", null, "Precision, by area"), h("p", { class: "muted", style: { fontSize: "14px", marginTop: "8px" } }, "Of the people flagged, how many truly have a planted pattern."),
        h("div", { class: "bars" }, Object.entries(m.per_scenario).map(([k, v]) => pair(area[k], v.ours.precision, v.threshold_alert.precision)))),
      h("div", null, h("h3", null, "False alarms on stable people"), h("p", { class: "muted", style: { fontSize: "14px", marginTop: "8px" } }, "Share of people with no planted pattern who were flagged anyway."),
        h("div", { class: "bars" }, Object.entries(m.false_alarm_rate_stable_people.by_archetype).map(([k, v]) => pair(k.replace(/_/g, " "), v.ours, v.threshold, { lowerIsBetter: true }))))),
    sec("03", "Other checks"),
    h("div", { class: "bignum" }, [
      [`+${Math.round(m.onset_lag_days.median)} d`, "median lag to detect onset", `${pct(m.onset_lag_days.within_60_days)} within 60 days`],
      [`${m.missing_data_requests.patients_with_removed_data}/${m.missing_data_requests.patients_with_removed_data}`, "removed data, all asked for", "labs and wearables deliberately dropped"],
      [`${m.guardrails.with_banned_phrase}/${m.guardrails.explanations_checked}`, "explanations with diagnosis wording", "fixed disclaimer on all"],
      [pct(m.robustness_no_wearable_sheet.still_surfaced.htn), "hypertension survives no wearable", `diabetes ${pct(m.robustness_no_wearable_sheet.still_surfaced.t2d)}`]].map(big)),
    sec("04", "Known limits"),
    h("ul", { class: "list-x" }, ["The “meaningful change” sizes and the three-signal rule are our choices and need clinical review.", "Quiet by design: subtle or short-lived changes are missed, and a change must still be present in the last 60 days.", "The baseline is the first 60 days, so a person already unwell then will have their change under-stated.", "Labs (about 5 a year) and cycles (about 12 a year) are sparse; those parts are the least certain.", "History linking is keyword-based and can miss unusual wording."].map((t) => h("li", null, t))));
  requestAnimationFrame(() => requestAnimationFrame(() => root.querySelectorAll(".fill").forEach((f) => { f.style.width = f.dataset.w; })));
  return root;
}
