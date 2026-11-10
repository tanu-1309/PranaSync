// The patient's own record, one function per page of the portal.
import { h, clear, STATUS, AREAS, chip, md, fmt, signed, fmtDate, parseDate, DAY } from "./ui.js";
import { hero } from "./hero.js";
import { glance } from "./glance.js";
import { convergence, convergenceKey, linePanel, labCard, patternSignals, onsets } from "./charts.js";

const GROUPS = ["Heart", "Body", "Movement", "Rest"];

export function pagehead(title, text) {
  return h("header", { class: "pagehead" }, h("h1", null, title), text ? h("p", null, text) : null);
}
const fold = (n, title, text, open, id, ...kids) => h("details", { class: "fold", open: open || null, id },
  h("summary", null, h("span", { class: "sn" }, n), h("h2", null, title), h("span", { class: "hint" }, "show or hide")), text ? h("p", { class: "foldtext" }, text) : null, ...kids);
const sec = (n, title, text) => h("header", { class: "sec" }, h("span", { class: "sn" }, n), h("h2", null, title), text ? h("p", null, text) : null);

// ------------------------------------------------------------------ headline
function headline(p, mode) {
  const you = mode !== "clinician";
  const surfaced = p.scenarios.filter((x) => x.surfaced);
  const ctxOf = (sc) => sc.context.find((c) => c.type !== "symptoms" && !/during/.test(c.timing || ""));
  if (surfaced.length) {
    const first = onsets(p).map((o) => o.date).sort()[0];
    const parts = surfaced.map((sc) => {
      const c = ctxOf(sc);
      return `${AREAS[sc.scenario].name.toLowerCase()} (${sc.pattern_signals.length} signals${sc.status === "pattern_with_context" && c ? `, echoing “${c.text}”` : ""})`;
    });
    const n = surfaced.length;
    return you ? {
      title: n === 1 ? "One area shows a pattern worth raising with your doctor." : `${n} areas show a pattern worth raising with your doctor.`,
      text: `Several of your measurements began moving together around ${fmtDate(first, "short")}: ${parts.join("; ")}. This describes what changed in your own data. It is not a diagnosis.`,
    } : {
      title: n === 1 ? "One area shows a multi-signal pattern." : `${n} areas show a multi-signal pattern.`,
      text: `Related signals began changing together around ${fmtDate(first, "short")}: ${parts.join("; ")}. Non-diagnostic; evidence below.`,
    };
  }
  const stable = p.scenarios.find((x) => x.status === "known_context_stable");
  if (stable) {
    const c = ctxOf(stable);
    return you ? { title: "Nothing is moving together.", text: `${c ? `Your record notes “${c.text}”, and ` : ""}your day-to-day numbers have stayed close to your usual. We keep watching, and say nothing when there is nothing to say.` }
      : { title: "Context on record, data stable.", text: `${c ? `History includes “${c.text}”; ` : ""}ongoing signals remain within personal baseline.` };
  }
  return you ? { title: "No multi-signal pattern found.", text: "None of the related measurements we check has moved away from your own usual in a lasting way." }
    : { title: "No multi-signal pattern found.", text: "No group of related signals has shifted from personal baseline in a lasting way." };
}

// ------------------------------------------------------------------ overview
const unitOf = (p, sig) => p.series[sig]?.unit || p.labs[sig]?.unit || "";

function movedRow(p, e) {
  let from, to, dv;
  if (e.kind === "daily") { from = e.baseline_mean; to = e.recent_mean; dv = e.change_pct; }
  else if (e.kind === "lab") { from = e.first; to = e.last; dv = from ? ((to - from) / from) * 100 : null; }
  else { from = e.baseline_mean; to = e.recent_mean; dv = from ? ((to - from) / from) * 100 : null; }
  const up = (to ?? 0) >= (from ?? 0);
  const u = e.kind === "cycle" ? "days" : unitOf(p, e.signal);
  return h("div", { class: "mv" },
    h("span", { class: "arr", "aria-hidden": "true" }, up ? "▲" : "▼"),
    h("span", { class: "nm" }, e.label.replace(/\s*\(.*\)$/, ""), h("small", null, `${fmt(from, 2)} → ${fmt(to, 2)} ${u}`.trim(), e.onset_date ? ` · from ${fmtDate(e.onset_date, "short")}` : "")),
    h("span", { class: "pc" }, `${signed(dv, 0)}%`, h("small", null, e.kind === "lab" ? "lab trend" : e.kind === "cycle" ? "cycle length" : "30-day mean")));
}
function threadItem(c) {
  const t = c.timing || "";
  return h("li", null,
    h("div", { class: "when" }, c.date ? fmtDate(c.date, "med") : "On record", /before/.test(t) ? h("div", { class: "tag before" }, "before pattern") : /during/.test(t) ? h("div", { class: "tag during" }, "during pattern") : null),
    h("div", null, h("div", { class: "what" }, c.text), c.detail ? h("div", { class: "det" }, c.detail) : null));
}
function evidenceTable(p, sc) {
  const rows = sc.evidence.map((e) => {
    const lab = e.kind === "lab";
    return h("tr", null, h("td", null, e.label), h("td", null, e.kind),
      h("td", { class: "r" }, fmt(lab ? e.first : e.baseline_mean, 2)), h("td", { class: "r" }, fmt(lab ? e.last : e.recent_mean, 2)),
      h("td", { class: "r" }, signed(e.change, 2)), h("td", { class: "r" }, e.change_pct != null ? `${signed(e.change_pct, 1)}%` : "—"),
      h("td", { class: "r" }, e.effect_size != null ? fmt(e.effect_size, 2) : "—"),
      h("td", { class: "r" }, e.trend_p != null ? (e.trend_p < 0.001 ? "<0.001" : fmt(e.trend_p, 3)) : "—"),
      h("td", { class: "r" }, e.coverage != null ? `${Math.round(e.coverage * 100)}%` : "—"),
      h("td", { class: "r" }, e.onset_date ? fmtDate(e.onset_date, "short") : "—"));
  });
  return h("div", { class: "tscroll" }, h("table", { class: "ev" },
    h("thead", null, h("tr", null, ["Signal", "Type", "Earlier", "Recent", "Change", "Change %", "Effect (SD)", "Trend p", "Coverage", "Started"].map((t, i) => h("th", { class: i > 1 ? "r" : "" }, t)))),
    h("tbody", null, rows)));
}
function allSignalsTable(p, sc) {
  const rows = Object.entries(sc.signals).map(([k, a]) => h("tr", null, h("td", null, p.labels[k] || k),
    h("td", null, a.status.replace(/_/g, " ")), h("td", null, a.direction ? `${a.direction} is a concern` : "—"),
    h("td", { class: "r" }, a.change != null ? signed(a.change, 2) : "—"), h("td", { class: "r" }, a.coverage != null ? `${Math.round(a.coverage * 100)}%` : "—")));
  return h("div", { class: "tscroll" }, h("table", { class: "ev" }, h("thead", null, h("tr", null, ["Signal", "Verdict", "Direction", "Change", "Coverage"].map((t, i) => h("th", { class: i > 2 ? "r" : "" }, t)))), h("tbody", null, rows)));
}

function finding(p, sc, mode) {
  const clin = mode === "clinician";
  const ctx = sc.context.filter((c) => c.type !== "symptoms" || clin);
  const body = h("div", { class: "fbody" }, h("div", { class: "prose" }, md(sc.explanation?.text)));
  if (sc.evidence.length) body.append(h("div", { class: "lbl" }, "What moved"), h("div", { class: "moved" }, sc.evidence.map((e) => movedRow(p, e))));
  if (ctx.length) body.append(h("div", { class: "lbl" }, "Linked history and context"), h("ul", { class: "thread" }, ctx.map(threadItem)));
  if (sc.missing_data.length) body.append(h("div", { class: "lbl" }, "What would help"),
    h("div", { class: "asks" }, sc.missing_data.map((m) => h("div", { class: "ask" }, h("b", null, m.item), h("span", null, m.reason)))));
  if (clin && sc.evidence.length) body.append(h("details", { class: "more", open: true }, h("summary", null, "Evidence used"), h("div", { class: "inner" }, evidenceTable(p, sc))));
  if (clin) body.append(h("details", { class: "more" }, h("summary", null, `All ${Object.keys(sc.signals).length} signals checked`), h("div", { class: "inner" }, allSignalsTable(p, sc))));
  body.append(h("details", { class: "more" }, h("summary", null, "Limits of this reading"), h("div", { class: "inner" }, h("ul", { class: "lims" }, sc.limitations.map((l) => h("li", null, l))))));
  return h("article", { class: `finding ${sc.surfaced ? "hot" : ""}`, id: `ins-${sc.scenario}` },
    h("aside", { class: "fside" }, h("h3", null, AREAS[sc.scenario].name), h("div", { class: "fsub" }, AREAS[sc.scenario].sub), chip(sc.status),
      sc.surfaced ? h("div", { class: "fmono" }, `${sc.pattern_signals.length} signals · from ${fmtDate(sc.pattern_start, "short")}`) : null),
    body);
}

// ------------------------------------------------------------------ reference values
const FLAG_TONE = { within: "teal", watch: "gold", outside: "ember" };
const CHANGE_TEXT = { changed: "Changed for you", improving: "Improving for you", stable: "Steady for you" };
const trimUnit = (s) => String(s).replace(/\s*\(.*\)$/, "");

function refRow(it, clin) {
  const level = h("td", { class: "r lv" }, h("b", null, it.value_text), h("span", { class: "faint" }, ` ${it.unit}`), h("div", { class: "faint asof" }, it.as_of));
  return h("tr", null,
    h("td", { class: "nm" }, trimUnit(it.label), it.soft ? h("small", null, "general guide") : null), level,
    h("td", { class: "rf" }, it.reference_text),
    h("td", null, h("span", { class: `mark tone-${FLAG_TONE[it.flag]}` }, it.category)),
    h("td", { class: it.relation === "steady_outside" && !it.soft ? "steady" : "" }, CHANGE_TEXT[it.change] || h("span", { class: "faint" }, "Not tracked for change")),
    clin ? h("td", { class: "src" }, it.source) : null);
}
function refTable(items, clin) {
  return h("div", { class: "tscroll" }, h("table", { class: "reft" },
    h("thead", null, h("tr", null, ["Measure", "Recent level", "Usual reference", "Where it sits", "Compared with your own usual"].concat(clin ? ["Source"] : []).map((x, i) => h("th", { class: i === 1 ? "r" : "" }, x)))),
    h("tbody", null, items.map((it) => refRow(it, clin)))));
}
function simpleReference(R) {
  const rank = { outside: 0, watch: 1, within: 2 };
  const off = R.items.filter((i) => i.flag !== "within").sort((a, b) => rank[a.flag] - rank[b.flag]);
  const ok = R.items.filter((i) => i.flag === "within");
  const card = (it) => h("div", { class: `lv-card tone-${FLAG_TONE[it.flag]}` },
    h("b", null, trimUnit(it.label)), h("span", { class: "lvv" }, it.value_text, h("small", null, ` ${it.unit}`)),
    h("span", { class: `mark tone-${FLAG_TONE[it.flag]}` }, it.category), h("small", null, it.reference_text));
  return h("div", { class: "refsec" },
    h("p", { class: "standfirst" }, `${ok.length} of ${R.items.length} measures are within their usual ranges.`, off.length ? ` ${off.length} ${off.length === 1 ? "is" : "are"} not:` : ""),
    off.length ? h("div", { class: "lvgrid" }, off.map(card)) : null,
    ok.length ? h("details", { class: "why" }, h("summary", null, `Show the ${ok.length} that are within range`), h("div", { class: "lvgrid" }, ok.map(card))) : null,
    h("p", { class: "fine" }, "Usual ranges are general guides from published guidelines and can differ with age, sex, pregnancy and medicines. They say where a number sits. They do not diagnose. Switch to Clinician view for sources."));
}

function referenceSection(p, mode) {
  const R = p.reference;
  if (!R || !R.items.length) return null;
  const clin = mode === "clinician";
  if (!clin) return simpleReference(R);
  const rank = { outside: 0, watch: 1, within: 2 };
  const off = R.items.filter((i) => i.flag !== "within").sort((a, b) => rank[a.flag] - rank[b.flag]);
  const ok = R.items.filter((i) => i.flag === "within");
  const total = R.items.length;
  const steady = R.items.filter((i) => R.steady_outside.includes(i.key));
  const nameList = (arr) => arr.map((i) => trimUnit(i.label)).join(", ");
  return h("div", { class: "refsec" },
    h("div", { class: "twoq" },
      h("div", null, h("b", null, "Has it changed for you?"), h("p", null, "Compares each signal with your own first 60 days. This is how patterns are found.")),
      h("div", null, h("b", null, "Is the level within a usual range?"), h("p", null, "Compares your recent level with general reference ranges from published guidelines."))),
    h("p", { class: "standfirst", style: { fontSize: "18px", marginTop: "22px" } },
      `${ok.length} of ${total} measures sit within their usual ranges. `, off.length ? `${off.length} ${off.length === 1 ? "sits" : "sit"} outside: ${nameList(off)}.` : "None sit outside."),
    steady.length ? h("div", { class: "note", style: { marginTop: "18px", maxWidth: "70ch" } }, h("b", null, "Steady, but outside the usual range: "), `${nameList(steady)}. These haven’t changed for you, so the pattern check would never raise them, yet the level itself is worth mentioning to your doctor if you haven’t already.`) : null,
    off.length ? h("div", { style: { marginTop: "22px" } }, refTable(off, clin)) : null,
    ok.length ? h("details", { class: "more" }, h("summary", null, `Show the ${ok.length} measures within their usual ranges`), h("div", { class: "inner" }, refTable(ok, clin))) : null,
    h("p", { class: "fine", style: { marginTop: "20px" } }, `Reference ranges are general guides and can differ with age, sex, pregnancy, medicines and health conditions; your lab’s own range may differ too. They say where a number sits. They do not diagnose. ${R.personal_only?.length ? "A few signals (heart-rate variability, weight, stress score, sedentary time) have no population range worth comparing with, so they are judged against you only." : ""}${clin ? " Sources are listed in the last column." : ""}`));
}

export function overviewView(p, mode) {
  const hl = headline(p, mode);
  const asksN = p.scenarios.reduce((a, sc) => a + sc.missing_data.length, 0);
  const list = p.scenarios.filter((x) => x.status !== "not_applicable").sort((a, b) => STATUS[a.status].rank - STATUS[b.status].rank);
  const goto = (id) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  const rows = p.scenarios.map((sc) => {
    const na = sc.status === "not_applicable";
    return h("tr", { class: na ? "na" : "" },
      h("td", { class: "nm" }, AREAS[sc.scenario].name, h("small", null, AREAS[sc.scenario].sub)),
      h("td", { class: "st" }, chip(sc.status)),
      h("td", { class: "ln" }, sc.surfaced ? `${sc.pattern_signals.length} signals moved together, from ${fmtDate(sc.pattern_start, "short")}.` : sc.status_text + ".",
        na ? null : h("div", null, h("button", { class: "link", style: { fontSize: "14px", marginTop: "4px" }, onclick: () => goto(`ins-${sc.scenario}`) }, "Read the finding ↓"))));
  });

  const earlier = p.events.filter((e) => e.t === "history" && e.d < p.start);
  return h("div", { class: "page home" },
    hero(p, hl),
    glance(p, hl),
    askBand(),
    h("h2", { class: "morehead" }, "Go deeper, when you want to"),
    fold("01", "Your year, week by week", "Each row is one measurement and each column a week. Colour shows how far that week sits from your own usual. A pattern is several rows warming together, not one hot cell.", false, "map",
      h("table", { class: "areas" }, h("tbody", null, rows)),
      h("div", { class: "cmap" }, h("div", { class: "keyrow" }, h("span", null, "Hover a column for the week’s readings."), convergenceKey()),
        convergence(p),
        earlier.length ? h("div", { class: "hist" }, h("b", null, "History on file"), earlier.map((e) => h("span", { class: "h" }, `${e.text}, ${fmtDate(e.d, "month")}`))) : null)),
    fold("02", "Where your levels sit", "Is each level within a usual range from published guidelines?", false, "levels", referenceSection(p, mode)),
    fold("03", "What we found", mode === "clinician" ? "Evidence-first. Every claim sits next to its effect size, trend test and coverage." : "In plain words: what changed, since when, and why it may matter.", p.scenarios.some((x) => x.surfaced), "found",
      h("div", null, list.map((sc) => finding(p, sc, mode)))),
    asksN ? h("p", { class: "standfirst" }, `${asksN} piece${asksN > 1 ? "s" : ""} of missing information would sharpen this picture. `, h("a", { class: "link", href: "#/help" }, "See what would help →")) : null,
    h("p", { class: "fine" }, "This describes patterns in your own data and does not diagnose. Please discuss anything here with a healthcare provider."));
}

// A calm invitation to the assistant, with a few things people usually want to know.
function askBand() {
  const ask = (q) => document.dispatchEvent(new CustomEvent("prana:ask", { detail: q }));
  return h("section", { class: "askband" },
    h("div", null, h("h2", null, "Not sure what something means?"), h("p", null, "Ask Prana in your own words. It answers from your record only, and never diagnoses.")),
    h("div", { class: "askchips" }, [["How am I doing?", "Give me a summary"], ["What are my health risks?", "What are my health risks?"], ["What changed for me?", "Did anything change for me?"], ["What should I ask my doctor?", "What should I ask my doctor?"]]
      .map(([l, q]) => h("button", { type: "button", onclick: () => ask(q) }, l))));
}

// ------------------------------------------------------------------ timeline
export function timelineView(p) {
  const hits = patternSignals(p);
  const state = { only: false, range: false };
  const host = h("div");
  const registry = new Map();
  const ranges = {};
  (p.reference?.items || []).forEach((it) => Object.assign(ranges, it.panel_ranges || {}));
  const draw = () => {
    clear(host); registry.clear();
    GROUPS.forEach((g) => {
      const keys = Object.keys(p.series).filter((k) => p.series[k].group === g && (!state.only || hits.has(k)));
      if (!keys.length) return;
      host.append(h("div", { class: "gtitle" }, g), h("div", null, keys.map((k, i) => linePanel(k, p, { registry, axis: i === keys.length - 1, hit: hits.has(k), range: state.range ? ranges[k] : null }))));
    });
    if (!host.childNodes.length) host.append(h("p", { class: "muted", style: { marginTop: "24px" } }, "No signals in a pattern."));
  };
  const btns = [["All signals", false], ["In a pattern", true]].map(([l, v]) => h("button", { "aria-pressed": String(v === false), disabled: v && !hits.size, onclick: (e) => {
    state.only = v; btns.forEach((b) => b.setAttribute("aria-pressed", String(b === e.currentTarget))); draw();
  } }, l));
  draw();
  return h("div", { class: "page" },
    pagehead("Timeline", "Every daily signal across the year. Move your pointer over any chart and all of them follow the same day."),
    h("div", { class: "tl-tools" },
      h("div", { class: "legend-line" },
        h("span", null, h("i", { class: "sw dots" }), "daily reading"), h("span", null, h("i", { class: "sw" }), "30-day mean"),
        h("span", null, h("i", { class: "sw band" }), "personal baseline ±1 SD"),
        onsets(p).length ? h("span", null, h("i", { class: "sw dash" }), "pattern begins") : null,
        p.meds.length ? h("span", null, h("span", { style: { color: "var(--blue)" } }, "▲"), "medicine started") : null),
      h("div", { style: { display: "flex", gap: "10px", flexWrap: "wrap" } }, h("div", { class: "tog" }, btns),
        h("div", { class: "tog", title: "Draw the general reference range behind each chart" }, h("button", { "aria-pressed": "false", onclick: (e) => {
          state.range = !state.range; e.currentTarget.setAttribute("aria-pressed", String(state.range)); draw();
        } }, "Show usual range")))),
    host);
}

// ------------------------------------------------------------------ labs & cycles
function cyclesBlock(p) {
  const cs = p.cycles.filter((c) => c.len != null);
  if (!cs.length) return null;
  const max = Math.max(45, ...cs.map((c) => c.len)) + 3, PH = 150;
  const plot = h("div", { class: "cycles", style: { height: `${PH + 40}px` } },
    h("div", { class: "band-note", style: { bottom: `${30 + (21 / max) * PH}px`, height: `${(14 / max) * PH}px` } }, h("small", null, "typical 21–35 days")));
  cs.forEach((c) => plot.append(h("div", { class: "cyc", title: `${fmtDate(c.d)} · ${c.len} days` },
    h("b", null, c.len), h("i", { class: c.len > 35 ? "long" : "", style: { height: `${(c.len / max) * PH}px` } }), h("span", null, fmtDate(c.d, "short").split(" ")[1]))));
  return h("section", { class: "cyc-wrap" }, h("h2", { style: { fontSize: "26px" } }, "Cycle length"),
    h("p", { class: "muted", style: { fontSize: "14.5px", marginTop: "6px", maxWidth: "58ch" } }, "Cycles over 35 days are drawn in vermilion. Lengthening cycles are one of the signals the women’s-health check watches."), plot);
}
export function labsView(p) {
  const hits = patternSignals(p);
  const keys = Object.keys(p.labs);
  return h("div", { class: "page" },
    pagehead("Labs and cycles", "Each result against its reference range. Dots on the line are individual results; the shaded band is the reference range."),
    keys.length ? h("div", { class: "labgrid" }, keys.map((k) => labCard(k, p.labs[k], p, { hit: hits.has(k) }))) : h("p", { class: "muted", style: { marginTop: "24px" } }, "No lab results on file."),
    cyclesBlock(p));
}

// ------------------------------------------------------------------ medications
// Plain wording only: one card per medicine (all its doses and changes together), words instead of symbols.
const MED_STATUS = { Active: "Taking now", Changed: "Replaced by a new dose or form", Stopped: "Stopped", Completed: "Course finished" };
const adherenceWords = (pct) => (pct >= 90 ? "Very consistent" : pct >= 80 ? "Mostly consistent" : pct >= 60 ? "Some missed doses" : "Many missed doses");
const adherenceTone = (pct) => (pct >= 80 ? "teal" : pct >= 60 ? "gold" : "ember");

function medicineCard(p, id, rows) {
  rows.sort((a, b) => (a.start || "").localeCompare(b.start || ""));
  const latest = rows[rows.length - 1];
  const now = !latest.end;
  const ad = p.adherence.filter((a) => a.med === id).sort((a, b) => a.d.localeCompare(b.d));
  const avg = ad.length ? Math.round(ad.reduce((s, a) => s + a.pct, 0) / ad.length) : null;
  const dose = (r) => `${r.name} ${r.dose}`.trim();

  const facts = h("dl", { class: "mfacts" },
    h("div", null, h("dt", null, "What it’s for"), h("dd", null, latest.for || "Not recorded")),
    h("div", null, h("dt", null, now ? "How you take it" : "How it was taken"), h("dd", null, `${dose(latest)}${latest.freq ? `, ${latest.freq.toLowerCase()}` : ""}`)),
    h("div", null, h("dt", null, now ? "Taking it since" : "Taken"), h("dd", null, now ? fmtDate(rows[0].start) : `${fmtDate(rows[0].start)} to ${fmtDate(latest.end)}`)),
    latest.tolerance ? h("div", null, h("dt", null, "How you’re coping with it"), h("dd", null, latest.tolerance)) : null);

  const body = h("div", { class: "mbody" }, facts);

  if (rows.length > 1) {
    body.append(h("h4", { class: "lbl" }, "What changed"), h("ol", { class: "mhist" }, rows.map((r, i) => h("li", null,
      h("span", { class: "mw" }, `${fmtDate(r.start)}${r.end ? ` to ${fmtDate(r.end)}` : " to now"}`),
      h("span", null, h("b", null, dose(r)), r.freq ? `, ${r.freq.toLowerCase()}` : "", " — ", MED_STATUS[r.status] || r.status,
        r.why ? h("span", { class: "faint" }, `. ${r.why}.`) : null,
        r.tolerance && i < rows.length - 1 ? h("span", { class: "faint" }, ` Side effect noted: ${r.tolerance}.`) : null)))));
  } else if (latest.why) {
    body.append(h("p", { class: "mnote" }, latest.why + "."));
  }

  if (ad.length) {
    body.append(h("h4", { class: "lbl" }, "Taking it as prescribed"),
      h("p", { class: "mnote" }, `Across the ${ad.length} records on file, you took about ${avg}% of your doses: `, h("span", { class: `mark tone-${adherenceTone(avg)}` }, adherenceWords(avg)), "."),
      h("div", { class: "tscroll" }, h("table", { class: "ev adh" },
        h("thead", null, h("tr", null, h("th", null, "Record date"), h("th", null, "Where it comes from"), h("th", { class: "r" }, "Doses taken"), h("th", { class: "r" }, "Doses missed"), h("th", null, "In words"))),
        h("tbody", null, ad.map((a) => h("tr", null, h("td", null, fmtDate(a.d)), h("td", { class: "faint" }, a.src || "—"), h("td", { class: "r" }, `${a.pct}%`), h("td", { class: "r" }, a.missed ?? "—"),
          h("td", null, h("span", { class: `mark tone-${adherenceTone(a.pct)}` }, adherenceWords(a.pct)))))))));
  } else body.append(h("p", { class: "faint mnote" }, "No adherence records for this medicine."));

  return h("article", { class: "med" },
    h("header", null, h("h3", null, latest.name), h("span", { class: `mark tone-${now ? "teal" : "slate"}` }, now ? "Taking now" : MED_STATUS[latest.status] || "Stopped")),
    body);
}

export function medsView(p) {
  const groups = new Map();
  p.meds.forEach((m) => { const k = m.id || m.name; groups.set(k, [...(groups.get(k) || []), m]); });
  const cards = [...groups].map(([id, rows]) => ({ id, rows, now: !rows.slice().sort((a, b) => (a.start || "").localeCompare(b.start || "")).pop().end }));
  const current = cards.filter((c) => c.now), past = cards.filter((c) => !c.now);
  const list = (arr) => h("div", { class: "medlist" }, arr.map((c) => medicineCard(p, c.id, c.rows)));
  return h("div", { class: "page" },
    pagehead("Medications", "The medicines on your record: what each one is for, how you take it, what has changed, and how consistently you have been taking it."),
    !cards.length ? h("p", { class: "muted", style: { marginTop: "24px" } }, "No medications on record.") : h("div", null,
      current.length ? h("div", null, h("h2", { class: "medh" }, `Taking now (${current.length})`), list(current)) : null,
      past.length ? h("div", null, h("h2", { class: "medh" }, `Stopped or finished (${past.length})`), list(past)) : null,
      h("p", { class: "fine" }, "Adherence figures are estimates (for example from pharmacy refills), not exact counts. Medicines are shown for context and are not yet used to adjust your baseline. Never change how you take a medicine because of this page; talk to your doctor or pharmacist first.")));
}

// ------------------------------------------------------------------ history
export function historyView(p) {
  const L = { history: "History", medications: "Medication", symptoms: "Symptom", notes: "Clinical note" };
  const ev = [...p.events].sort((a, b) => b.d.localeCompare(a.d));
  return h("div", { class: "page" },
    pagehead("History and notes", "Everything dated in your record, newest first: diagnoses, medicines, symptoms you logged, and clinical notes."),
    h("div", { class: "fullthread" }, h("ul", { class: "thread" }, ev.map((e) => h("li", null,
      h("div", { class: "when" }, fmtDate(e.d), e.d < p.start ? h("div", { class: "tag before" }, "before this record") : null),
      h("div", null, h("div", { class: "faint mono", style: { fontSize: "11.5px" } }, L[e.t] || e.t), h("div", { class: "what", style: { fontWeight: e.t === "history" ? 600 : 400 } }, e.text)))))));
}

// ------------------------------------------------------------------ what would help
export function helpView(p) {
  const asks = p.scenarios.flatMap((sc) => sc.missing_data.map((m) => ({ ...m, area: AREAS[sc.scenario].name })));
  return h("div", { class: "page" },
    pagehead("What would help", "When something is missing, we say so, and say why it matters, instead of guessing."),
    asks.length ? h("div", { class: "asklist" }, asks.map((m, i) => h("div", { class: "askrow" },
      h("span", { class: "n" }, String(i + 1).padStart(2, "0")), h("div", null, h("b", null, m.item), h("p", null, m.reason)), h("span", { class: "for" }, m.area))))
      : h("p", { class: "standfirst" }, "Nothing important is missing for the areas we check."),
    h("p", { class: "fine" }, "Adding new information and re-running the analysis is planned for a later release. For now, this list is something to bring to your care team."));
}

// ------------------------------------------------------------------ data quality
export function qualityView(p) {
  const q = p.quality;
  const bad = (q.vitals_impossible_values || 0) + (q.wearable_impossible_values || 0);
  const items = [
    ["Sheets found", `${q.sheets_found}/11`, q.sheets_found === 11 ? "ok" : "warn"], ["Vitals days", q.vitals_days], ["Wearable days", q.wearable_days],
    ["Blank vitals cells", q.vitals_blank_cells], ["Blank wearable cells", q.wearable_blank_cells],
    ["Impossible values removed", bad, bad ? "warn" : "ok"], ["Duplicate days merged", (q.vitals_duplicate_days || 0) + (q.wearable_duplicate_days || 0)],
    ["Lab rows", q.lab_rows], ["Cycles logged", q.cycles], ["Lab unit conversions", q.lab_unit_conversions],
  ];
  return h("div", { class: "page" },
    pagehead("Data quality", "Every cleaning step is counted rather than hidden, so you can see how complete the record behind your analysis is."),
    h("div", { class: "qgrid" }, items.map(([l, v, t]) => h("div", { class: `q ${t || ""}` }, h("div", { class: "v" }, v ?? 0), h("div", { class: "l" }, l)))),
    h("p", { class: "fine" }, `Missing sheets: ${q.missing_sheets?.length ? q.missing_sheets.join(", ") : "none"}.`));
}
