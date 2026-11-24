// The extra sections on Home, written from a patient's point of view: the numbers worth knowing, what would help, a snapshot of care, and when to get help now.
// Plain words, one idea per card, and nothing that depends on colour alone.
import { h, s, fmtDate, api, clear } from "./ui.js";

const trim = (s) => String(s).replace(/\s*\(.*\)$/, "");
const TONE = { within: "teal", watch: "gold", outside: "ember" };
const WORD = { within: "In the usual range", watch: "Close to the edge", outside: "Outside the usual range" };

const section = (id, title, lead, ...kids) => h("section", { class: "hp", id, tabindex: "-1", "aria-labelledby": `${id}-h` }, h("h2", { id: `${id}-h` }, title), lead ? h("p", { class: "standfirst" }, lead) : null, ...kids);

// Numbers to know: the measures outside their usual range first, each in one line a patient can read at a glance.
export function keyNumbers(p) {
  const items = p.reference?.items || [];
  if (!items.length) return null;
  const rank = { outside: 0, watch: 1, within: 2 };
  const off = items.filter((i) => i.flag !== "within").sort((a, b) => rank[a.flag] - rank[b.flag]);
  const ok = items.filter((i) => i.flag === "within");
  const card = (it) => h("li", { class: `kn tone-${TONE[it.flag]}` },
    h("span", { class: "kn-name" }, trim(it.label)),
    h("b", { class: "kn-val" }, it.value_text, h("small", null, ` ${it.unit}`)),
    h("span", { class: "kn-flag" }, h("i", { class: `kn-shape ${it.flag}`, "aria-hidden": "true" }), WORD[it.flag]),
    h("span", { class: "kn-ref" }, it.reference_text));
  return section("levels-home", "Numbers worth knowing",
    `${ok.length} of ${items.length} measures are in their usual range.${off.length ? ` ${off.length === 1 ? "This one is" : "These are"} not:` : " Nothing is outside."}`,
    off.length ? h("ul", { class: "kn-grid" }, off.map(card)) : null,
    ok.length ? h("details", { class: "why" }, h("summary", null, `Show the ${ok.length} that are in range`), h("ul", { class: "kn-grid" }, ok.map(card))) : null,
    h("p", { class: "fine" }, "Usual ranges are general guides and can differ with age, sex, pregnancy and medicines. ", h("a", { href: "#/records/labs" }, "Compare every measure in Labs")));
}

// What would help: everything that is missing in one place, in the order that adds the most, each with a clear next step.
export function whatWouldHelp(p, risk) {
  const asks = (p.scenarios || []).flatMap((sc) => (sc.missing_data || []).map((m) => ({ item: m.item, why: m.reason })));
  const miss = risk?.available ? risk.missing || [] : [];
  const ups = risk?.available ? risk.next_uploads || [] : [];
  const given = (p.scenarios || []).flatMap((sc) => (sc.provided_data || []).map((m) => ({ item: m.item, from: m.from })));
  const none = !asks.length && !miss.length;
  const kids = [];
  if (ups.length) kids.push(h("div", { class: "wh-col" }, h("h3", null, "Documents that would add the most"),
    h("ol", { class: "wh-list" }, ups.slice(0, 3).map((u) => h("li", null, h("b", null, u.help))))));
  if (miss.length) kids.push(h("div", { class: "wh-col" }, h("h3", null, "Values we are missing for your risk estimates"),
    h("p", { class: "wh-chips" }, miss.slice(0, 12).map((m) => h("span", { class: "chip-miss" }, m.label)))));
  if (asks.length) kids.push(h("div", { class: "wh-col" }, h("h3", null, "Results that would sharpen your record"),
    h("ul", { class: "wh-list plain" }, asks.slice(0, 6).map((a) => h("li", null, h("b", null, a.item), h("span", null, a.why))))));
  if (given.length) kids.unshift(h("div", { class: "wh-col wh-done" }, h("h3", null, "Now provided by your documents"),
    h("ul", { class: "wh-list plain" }, given.map((g) => h("li", null, h("b", null, g.item), h("span", null, g.from ? `from ${g.from}` : ""))))));
  return section("help-home", "What would help", none ? "Your record has what we look at. Add newer documents any time and everything updates." : "Adding these would make your picture more complete and your estimates stronger.",
    kids.length ? h("div", { class: "wh-grid" }, kids) : null,
    h("div", { class: "wh-cta" }, h("a", { class: "btn solid", href: "#/upload" }, "Upload a document"), h("span", { class: "fine" }, "PDF, Word, text, CSV or Excel. One at a time is fine.")));
}

// Care at a glance: medicines, allergies, latest symptoms and how much the record covers. Small tiles, each with a link to its page.
export function careTiles(p) {
  const active = (p.meds || []).filter((m) => m.status === "Active" || m.status === "Changed" && !m.end);
  const taken = (p.adherence || []).map((a) => a.pct);
  const adh = taken.length ? Math.round(taken.reduce((a, b) => a + b, 0) / taken.length) : null;
  const sym = (p.events || []).filter((e) => e.t === "symptoms").sort((a, b) => (a.d < b.d ? 1 : -1))[0];
  const labs = Object.values(p.labs || {}).flatMap((l) => (l.points || l.rows || []).map((r) => r.d || r[0])).filter(Boolean).sort();
  const tile = (title, big, small, href, label) => h("a", { class: "ct", href }, h("span", { class: "gk" }, title), h("b", null, big), h("span", null, small), h("span", { class: "gf" }, label));
  return section("care-home", "Your care at a glance", null, h("div", { class: "ct-grid" },
    tile("Medicines", active.length ? `${active.length} current` : "None on record", active.length ? active.slice(0, 3).map((m) => m.name).join(", ") + (adh != null ? ` · about ${adh}% of doses taken` : "") : "Nothing recorded as current.", "#/records/medicines", "Review all your medicines"),
    tile("Allergies", p.profile?.allergies || "Not recorded", p.profile?.family ? `Family history: ${p.profile.family}` : "No family history recorded.", "#/records/history", "Read your history and notes"),
    tile("Latest symptom note", sym ? sym.text : "None recorded", sym ? fmtDate(sym.d, "med") : "", "#/records/history", "Read your history and notes"),
    tile("Record covers", `${fmtDate(p.window[0], "month")} to ${fmtDate(p.window[1], "month")}`, labs.length ? `Latest lab result ${fmtDate(labs[labs.length - 1], "med")}` : "Daily readings and lab results", "#/records/trends", "Explore your trends")));
}

// When to get help now: always visible, short, and the same wording a clinic would use.
export function urgentBox() {
  return h("aside", { class: "urgent", "aria-label": "When to get urgent help" },
    h("b", null, "When to get help now"),
    h("p", null, "Chest pain, trouble breathing, signs of a stroke (face drooping, weak arm, slurred speech), fainting, or very high or very low blood sugar with feeling unwell: call your local emergency number. This page cannot give emergency help."));
}

// First steps for someone who has just registered and has not uploaded anything yet.
export function startSteps() {
  return h("section", { class: "hp steps", "aria-labelledby": "steps-h" }, h("h2", { id: "steps-h" }, "Start in three steps"),
    h("ol", { class: "st-list" },
      h("li", null, h("b", null, "Upload one document"), h("span", null, "A lab report, a clinic visit note or a tracker export. One is enough to get started.")),
      h("li", null, h("b", null, "Check what we read"), h("span", null, "Every value is shown with the line it came from. Remove the document if something is wrong.")),
      h("li", null, h("b", null, "Add more over time"), h("span", null, "Each new document makes the three estimates stronger and fills in what is missing."))),
    h("a", { class: "btn solid", href: "#/upload" }, "Upload your first document"));
}

// The values we hold for a person who builds their record by uploading: what, how much, from which document.
export function yourValues(risk) {
  const known = [...(risk?.known || []), ...(risk?.extra_known || [])];
  if (!known.length) return null;
  return section("values-home", "Values we have from your documents", `${known.length} values from ${risk.documents} document${risk.documents === 1 ? "" : "s"}. Newest value wins when a document repeats one.`,
    h("div", { class: "tscroll" }, h("table", { class: "up-table" }, h("thead", null, h("tr", null, ["Parameter", "Value", "From"].map((t) => h("th", { scope: "col" }, t)))),
      h("tbody", null, known.map((k) => h("tr", null, h("th", { scope: "row" }, k.label), h("td", null, k.text), h("td", { class: "faint" }, k.from || "")))))));
}

// Fills itself in once the risk estimates arrive, so the page does not wait for them.
export function helpAsync(p) {
  const host = h("div", { class: "hp-host" }, whatWouldHelp(p, null));
  api("risk", { fresh: true }).then((r) => { clear(host); host.append(whatWouldHelp(p, r)); }).catch(() => {});
  return host;
}

// A tiny line for one value across documents: evenly spaced, oldest to newest, with the last point filled.
function spark(points, label) {
  const W = 120, H = 34, vs = points.map((p) => p.value), lo = Math.min(...vs), hi = Math.max(...vs), span = hi - lo || 1;
  const xy = points.map((p, i) => [4 + (i * (W - 8)) / Math.max(1, points.length - 1), H - 5 - ((p.value - lo) / span) * (H - 10)]);
  return s("svg", { viewBox: `0 0 ${W} ${H}`, class: "spark", role: "img", "aria-label": `${label}: ${points.map((p) => p.text).join(", then ")}` },
    s("polyline", { points: xy.map((q) => q.join(",")).join(" "), fill: "none", "stroke-width": 2, class: "spark-l" }),
    ...xy.map((q, i) => s("circle", { cx: q[0], cy: q[1], r: i === xy.length - 1 ? 3.6 : 2.4, class: i === xy.length - 1 ? "spark-d last" : "spark-d" })));
}

// How each value changed between the documents someone uploaded. A description of two documents, not a diagnosis.
export function valueHistory(rows, documents) {
  const multi = (rows || []).filter((r) => r.points.length > 1);
  if (!rows?.length) return null;
  if (!multi.length) return section("history-home", "How your values change", "Upload a newer document with the same values and this shows what changed between them.",
    h("p", { class: "note" }, `You have ${documents} document${documents === 1 ? "" : "s"} so far. Each value appears once.`));
  return section("history-home", "How your values changed between documents", "Each row follows one value across your uploaded documents, oldest to newest. This describes two or more documents. It is not a diagnosis.",
    h("div", { class: "tscroll" }, h("table", { class: "mt ct-table" }, h("caption", { class: "sr" }, "Values across documents"),
      h("thead", null, h("tr", null, ["Value", "First", "Latest", "Change", "Over time"].map((c) => h("th", { scope: "col" }, c)))),
      h("tbody", null, multi.map((r) => {
        const a = r.points[0], b = r.points[r.points.length - 1], dir = r.change_pct == null || r.change_pct === 0 ? "no change" : r.change_pct > 0 ? `▲ ${r.change_pct}% higher` : `▼ ${Math.abs(r.change_pct)}% lower`;
        return h("tr", null, h("th", { scope: "row" }, r.label), h("td", null, a.text, h("small", { class: "faint" }, a.date ? ` ${fmtDate(a.date, "med")}` : "")), h("td", null, h("b", null, b.text), h("small", { class: "faint" }, b.date ? ` ${fmtDate(b.date, "med")}` : "")),
          h("td", { class: `hv-${r.change_pct > 0 ? "up" : r.change_pct < 0 ? "down" : "flat"}` }, dir), h("td", null, spark(r.points, r.label)));
      })))));
}

// Fetches the history and fills itself in, so a page does not wait for it.
export function historyAsync() {
  const host = h("div", { class: "hp-host" });
  api("values/history", { fresh: true }).then((r) => { const el = valueHistory(r.values, r.documents); if (el) host.append(el); }).catch(() => {});
  return host;
}
