// Makes the important words in a piece of text easy to find: the values with their units, the measures they belong to, and the direction words (above, within, outside, rising…).
// It reads **double-asterisk** marks when the AI model wrote them, and finds the same kinds of words itself when it did not, so older stored text looks the same as new text.
// Nothing here uses innerHTML: the text is split into plain text nodes and <span>/<strong> elements, so odd characters in a document or an AI answer cannot inject markup.
import { h } from "./ui.js";

const UNIT = "(?:mg/dL|mmol/L|mmol/mol|mmHg|kg/m²|kg/m2|bpm|steps|hours|h/night|min|kg|cm|per week|%)";
const VALUE = new RegExp(String.raw`\b\d{2,3}/\d{2,3}\s?mmHg|\b\d[\d,]*(?:\.\d+)?\s?${UNIT}(?![A-Za-z])|\b\d[\d,]*(?:\.\d+)?\s?%`, "gi");
const MEASURES = ["HbA1c", "fasting glucose", "blood sugar", "LDL cholesterol", "HDL cholesterol", "total cholesterol", "cholesterol", "triglycerides", "blood pressure", "systolic", "diastolic",
  "body mass index", "BMI", "resting heart rate", "heart rate", "sleep", "daily steps", "steps", "eGFR", "TSH", "vitamin D", "testosterone", "cycle length", "weight"];
const UP = ["above typical", "well above typical", "above the usual range", "well above the typical range", "above the typical range", "outside the usual range", "outside its usual range", "outside the typical range", "outside its typical range", "above", "elevated"];
const OK = ["within the usual range", "within its usual range", "within the typical range", "within its typical range", "within range", "improving"];
const MID = ["moderate", "close to the edge", "near the edge", "borderline", "limited", "fair"];
const DIR = ["higher", "lower", "raises", "lowers", "rising", "falling", "increase", "increased", "decrease", "decreased", "below", "steady", "stable"];   // direction words: bold, no colour, because whether they are good depends on the measure
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const words = (list) => list.slice().sort((a, b) => b.length - a.length).map(esc).join("|");
const TERM = new RegExp(String.raw`\b(?:${words(MEASURES)})\b`, "gi");
const TONE = [[new RegExp(String.raw`\b(?:${words(UP)})\b`, "gi"), "hl-up"], [new RegExp(String.raw`\b(?:${words(OK)})\b`, "gi"), "hl-ok"], [new RegExp(String.raw`\b(?:${words(MID)})\b`, "gi"), "hl-mid"], [new RegExp(String.raw`\b(?:${words(DIR)})\b`, "gi"), "hl-dir"]];

function toneOf(s) {
  for (const [rx, cls] of TONE) { rx.lastIndex = 0; if (rx.test(s)) return cls; }
  return "";
}

// Find every highlight in a plain string: [start, end, class]. Earlier kinds win where they overlap (values, then measures, then direction words).
function spans(text) {
  const found = [];
  const take = (rx, cls) => {
    rx.lastIndex = 0;
    for (let m = rx.exec(text); m; m = rx.exec(text)) {
      const a = m.index, b = a + m[0].length;
      if (!found.some(([x, y]) => a < y && b > x)) found.push([a, b, typeof cls === "function" ? cls(m[0]) : cls]);
      if (m[0].length === 0) rx.lastIndex++;
    }
  };
  take(VALUE, "hl-val"); take(TERM, "hl-term");
  TONE.forEach(([rx, cls]) => take(rx, cls));
  return found.sort((p, q) => p[0] - q[0]).slice(0, 10);       // at most ten per piece, so nothing is highlighted into noise
}

function plain(text) {
  const out = [];
  let at = 0;
  for (const [a, b, cls] of spans(text)) {
    if (a > at) out.push(text.slice(at, a));
    out.push(h("span", { class: `hl ${cls}` }, text.slice(a, b)));
    at = b;
  }
  if (at < text.length) out.push(text.slice(at));
  return out;
}

// highlight("HbA1c is **6.32 %**, above typical") -> a list of nodes you can pass to h(...)
export function highlight(text) {
  if (text == null || text === "") return [];
  const s = String(text);
  const out = [];
  const parts = s.split(/(\*\*[^*]+\*\*)/g);
  const marked = parts.some((p) => /^\*\*[^*]+\*\*$/.test(p));
  for (const p of parts) {
    const m = /^\*\*([^*]+)\*\*$/.exec(p);
    if (m) out.push(h("strong", { class: `hl hl-mark ${toneOf(m[1])}` }, m[1]));
    else out.push(...(marked ? [p] : plain(p)));                // the model's own marks are trusted; only unmarked text is highlighted automatically
  }
  return out;
}

export const hl = (tag, attrs, text) => h(tag, attrs, ...highlight(text));

// A one-line key for the colours, for pages that use highlights.
export function highlightKey() {
  return h("p", { class: "hl-key", "aria-label": "How highlights are used" }, h("span", { class: "hl hl-val" }, "6.3 %"), " a value · ", h("span", { class: "hl hl-term" }, "HbA1c"), " a measure · ",
    h("span", { class: "hl hl-up" }, "above"), " higher or outside the usual range · ", h("span", { class: "hl hl-ok" }, "within"), " in range or lower · ", h("span", { class: "hl hl-mid" }, "moderate"), " in between");
}
