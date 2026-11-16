// How it works → The models. Which model does which job, why it matters, and how well each was checked. Every number comes from a file the project produced
// (results/metrics.json, results/forecast_backtest.json, models/risk_model.json); where nothing was measured the page says so instead of inventing a figure.
import { h, api, pct } from "./ui.js";

const AREA = { heart: "Heart and circulation", diabetes: "Blood sugar (diabetes)", blood_pressure: "Blood pressure" };
const auc = (v) => (v == null ? "—" : v.toFixed(2));

function part(kind, tone, title, job, why, checked, know) {
  return h("article", { class: "mp" },
    h("span", { class: `mp-kind tone-${tone}` }, kind), h("h3", null, title),
    h("dl", null, h("dt", null, "Its job"), h("dd", null, job), h("dt", null, "Why it matters"), h("dd", null, why), h("dt", null, "How it was checked"), h("dd", null, checked), h("dt", null, "Keep in mind"), h("dd", null, know)));
}

function importance(r) {
  return h("div", { class: "imp-grid" }, Object.entries(r.top_parameters).map(([area, list]) => h("div", { class: "imp" }, h("h3", null, AREA[area] || area),
    h("ol", null, list.map((p) => h("li", null, h("span", { class: "imp-n" }, p.label), h("span", { class: "imp-bar", role: "img", "aria-label": `${p.label}: ${Math.round(p.share * 100)} percent of the model's attention` }, h("i", { style: { width: `${Math.max(4, Math.round(p.share * 100))}%` } })), h("span", { class: "imp-v" }, `${Math.round(p.share * 100)}%`)))))));
}

function rails(list, rt) {
  if (!list.length) return h("p", { class: "note" }, "The rail list is not available.");
  const table = h("div", { class: "tscroll" }, h("table", { class: "mt ct-table" }, h("caption", { class: "sr" }, "The safeguard rails"),
    h("thead", null, h("tr", null, ["Rail", "What it does", "Applies to"].map((x) => h("th", { scope: "col" }, x)))),
    h("tbody", null, list.map((r) => h("tr", null, h("th", { scope: "row" }, `${r.id}  ${r.name}`), h("td", null, r.plain), h("td", null, r.when === "input" ? "What the model is given" : "What the model writes"))))));
  const test = rt ? h("div", { class: "ar-decision" }, h("b", null, "Red-team test: "), `${rt.passed} of ${rt.tested ?? rt.total} attacks that were tried held (${rt.chat_prompts} adversarial questions to the chat and ${rt.booby_trapped_documents} documents with hidden orders), on ${String(rt.model || "").replace(/^openai:/, "")}. `,
    rt.not_tested ? `${rt.not_tested} could not be tried because the hosted model was rate-limited at the time: they are not counted as passed. ` : "",
    "That shows the rails held on these cases. It is not proof that no input can get through.") : h("p", { class: "note" }, "The red-team test has not been run yet (python scripts/redteam_ai.py).");
  return h("div", null, table, test);
}

export async function modelsView() {
  let m, v = null;
  try { [m, v] = await Promise.all([api("models"), api("validation").catch(() => null)]); }
  catch { return h("p", { class: "note" }, "The model details could not be loaded. Please try again in a moment."); }
  const r = m.risk, dc = r?.development_check, fc = m.forecast, o = v?.overall;
  const lm = m.language_models;
  const nice = (id, fallback) => (/nemotron/i.test(id || "") ? "NVIDIA Nemotron 3 Ultra" : /medgemma/i.test(id || "") ? "Google MedGemma 1.5 (4B)" : id || fallback);
  const text = nice(lm.text.name, "The text model"), ins = nice(lm.insights.model, "Google MedGemma 1.5 (4B)");

  const parts = h("div", { class: "mp-grid" },
    part("Statistics, no AI", "teal", "Pattern detection", "Compares each measurement with your own first 60 days and looks for several related ones moving away from your usual together.",
      "It is what makes a pattern worth raising, instead of a single high reading that sets off an alarm. It stays quiet when there is nothing to say.",
      o ? `Tested on ${v.n_patients} practice records where we planted the patterns ourselves: ${pct(o.ours.precision)} of the people it flagged really had a pattern (a simple alert: ${pct(o.threshold_alert.precision)}).` : "The test results are not available.",
      "Practice records are made up. It misses subtle or short-lived changes by design."),
    part("Machine learning", "violet", "Risk classes (heart, blood sugar, blood pressure)", "Places you as lower, moderate or higher for each area, and lists which of your values push the class up or down.",
      "It is the one part that gives a class from a single document, and it shows its reasons, so you can check them against your own numbers.",
      dc ? `Development check on ${r.n_patients} practice records, splitting by person: it ranks people with the recorded condition above people without it ${auc(dc.heart.complete)} (heart), ${auc(dc.diabetes.complete)} (blood sugar) and ${auc(dc.blood_pressure.complete)} (blood pressure) on a scale where 0.50 is a coin toss.` : "No development check is available.",
      "It learned from diagnoses written in practice records, not from what happened later. A class is not a diagnosis or a forecast, and no clinician has reviewed it."),
    part("AI language model", "gold", "Plain-language writer", `${text} writes your Home summary, the cards, the Outlook text and the questions for your doctor, from facts that code has already computed.`,
      "It turns numbers into words you can read, in the level you pick (plain language or clinician view).",
      "We have not measured its accuracy. We check every answer instead: each number it writes must appear in your facts, diagnosis wording and medicine advice are blocked, and an answer that fails is thrown away.",
      `In the safety test, ${v ? `${v.guardrails.with_banned_phrase} of ${v.guardrails.explanations_checked}` : "none of the"} checked explanations contained diagnosis wording. It runs through OpenRouter's free tier, so it can be slow or briefly unavailable.`),
    part("AI language model", "gold", "Medical insights", `${ins} reads your computed statistics and says what stands out, what made it say so, and how confident it is.`,
      "It adds general medical context to your numbers, with reasons you can read step by step.",
      "We have not measured its accuracy. Its output is checked the same way, and its stated confidence is lowered when the statistics do not support it.",
      "It runs on this computer, so your data stays here, but it takes minutes per person. Its medical background comes from the model’s memory and is labelled that way."),
    part("Statistics, no AI", "teal", "Trend watch and short forecast", "Shows where a measurement is heading, and a three-month projection only when the trend is very strong.",
      "A projection that is not earned would mislead, so the default is to say nothing.",
      fc ? `Back-tested on ${fc.patients} records: for daily measurements the projection beat “nothing changes” ${pct(fc.daily.better_than_nothing_changes)} of the time and the true value fell inside the shown range ${pct(fc.daily.inside_95_range)} of the time.` : "No back-test is available.",
      "Lab results have only a few values a year, so they are never projected."));

  const rows = [];
  if (dc) {
    Object.entries(dc).forEach(([area, x]) => rows.push([AREA[area] || area, "Ranking accuracy (AUC), all values present", auc(x.complete), "Pick one person with the recorded condition and one without: this is how often the model scores the first higher."]));
    const worst = Math.min(...Object.values(dc).flatMap((x) => Object.values(x.profile_plus_one_document)));
    const best = Math.max(...Object.values(dc).flatMap((x) => Object.values(x.profile_plus_one_document)));
    rows.push(["All three areas", "Ranking accuracy with age, sex and one document", `${auc(worst)} to ${auc(best)}`, "It still works from a single document, less sharply. The evidence bar says how much of the picture is in."]);
  }
  if (o) {
    rows.push(["Pattern detection", "Precision", pct(o.ours.precision), "Of the people it flagged, the share who truly had a planted pattern."]);
    rows.push(["Pattern detection", "Recall", pct(o.ours.recall), "Of the people with a planted pattern, the share it found."]);
    rows.push(["Pattern detection", "Stable people flagged", pct(v.false_alarm_rate_stable_people.ours), `False alarms on people with no pattern (a simple alert: ${pct(v.false_alarm_rate_stable_people.threshold_alert)}).`]);
  }
  if (fc) rows.push(["Forecast", "Inside the shown range", pct(fc.daily.inside_95_range), "How often the real value landed in the 95% range, for daily measurements that passed the strict gate."]);
  rows.push(["Language models", "Accuracy", "Not measured", "We check each answer against your facts instead (see the safeguards below)."]);
  const table = h("div", { class: "tscroll" }, h("table", { class: "mt" }, h("caption", { class: "sr" }, "How well each part was checked"),
    h("thead", null, h("tr", null, ["Part", "Measure", "Result", "What it means"].map((t) => h("th", { scope: "col" }, t)))),
    h("tbody", null, rows.map(([a, b, c, d]) => h("tr", null, h("th", { scope: "row" }, a), h("td", null, b), h("td", { class: "mt-v" }, c), h("td", null, d))))));

  return h("div", { class: "models" },
    h("section", { "aria-labelledby": "mdl-1" }, h("h2", { id: "mdl-1" }, "The parts, and what each one is for"), h("p", { class: "standfirst" }, "Code does the arithmetic. Models place, explain and write. Nothing here diagnoses."), parts),
    h("section", { "aria-labelledby": "mdl-2" }, h("h2", { id: "mdl-2" }, "How precise is each part?"),
      h("p", { class: "standfirst" }, "These are development checks on practice data, so they show the method works, not that it is clinically proven."), table),
    r ? h("section", { "aria-labelledby": "mdl-3" }, h("h2", { id: "mdl-3" }, "What the risk model pays most attention to"),
      h("p", { class: "standfirst" }, "The share of the model’s attention each measurement gets, for each area. This is why a document with those values gives a stronger answer."), importance(r),
      h("details", { class: "why" }, h("summary", null, "What “recorded as present” means for each area"),
        h("ul", { class: "list-x" }, Object.entries(r.definitions).map(([a, d]) => h("li", null, h("b", null, `${AREA[a]}: `), `${d}. About ${pct(r.prevalence[a])} of the practice records match.`))))) : null,
    h("section", { "aria-labelledby": "mdl-4" }, h("h2", { id: "mdl-4" }, "Safeguard rails on every AI answer"),
      h("p", { class: "standfirst" }, "A model only writes words. Code decides whether the words may be shown. An answer that breaks a rail is thrown away and you see the computed numbers instead."),
      rails(m.rails || [], m.redteam)),
    h("p", { class: "fine" }, "Practice data is synthetic. A clinician has not reviewed the measurements, directions, wording or thresholds. Please discuss anything here with a healthcare provider."));
}
