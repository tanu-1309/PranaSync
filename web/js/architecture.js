// How it works → Architecture. How a document goes from upload to risk class, where everything lives, who can open a document, how every AI answer is checked, and how we decide which reader is best.
// The flow diagrams are real lists (so a screen reader reads them in order) styled as boxes with arrows; the system map is an SVG with a written description beside it.
import { h, s, api, pct } from "./ui.js";

const TAGS = { you: ["You", "violet"], code: ["Runs here, no AI", "teal"], ai: ["AI model", "gold"], data: ["Stored", "slate"], ml: ["Trained model", "violet"] };

function node(n, title, text, tag, extra) {
  const [label, tone] = TAGS[tag];
  return h("li", { class: `fl-node tone-${tone}${extra ? ` ${extra}` : ""}` }, h("span", { class: "fl-n", "aria-hidden": "true" }, n), h("span", { class: "fl-tag" }, label), h("b", null, title), h("span", { class: "fl-t" }, text));
}
const flow = (label, rows) => h("div", { class: "fl-wrap" }, rows.map((r, i) => h("ol", { class: `fl-row${r.branch ? " branch" : ""}`, "aria-label": `${label}, part ${i + 1}` }, r.nodes)));
const fig = (id, title, lead, body, alt) => h("section", { class: "ar-sec", "aria-labelledby": id }, h("h2", { id }, title), h("p", { class: "standfirst" }, lead), body, alt ? h("details", { class: "why" }, h("summary", null, "Describe this diagram in words"), h("p", { class: "ar-alt" }, alt)) : null);

// ------------------------------------------------------------------ 1. upload to risk class
function uploadFlow(ex) {
  const ai = ex?.nemotron;
  return fig("ar-1", "What happens when you upload a document", "Eight steps, in order. Everything except the optional step 5 runs on this computer, including reading photos.",
    flow("Upload to risk class", [
      { nodes: [node(1, "You choose a file", "PDF, Word, text, CSV, Excel, or a photo or scan of a report.", "you"),
        node(2, "Safety checks", "Real file type, up to 10 MB, PDF up to 40 pages, no decompression bombs, not uploaded before, 15 uploads a minute, signed in (guests cannot upload).", "code"),
        node(3, "Read the text (OCR for pictures)", "PDF, Word and text become text; CSV and Excel tables become lines; photos and scanned pages are read on this computer by OCR. The text is kept so you can see what we saw.", "code"),
        node(4, "Pattern reader", "Finds 29 kinds of value by name (21 feed the risk classes, 8 are extra labs such as testosterone and LH/FSH), converts units (mmol/L to mg/dL, mmol/mol to %), drops impossible values, and keeps the line each one came from.", "code")] },
      { nodes: [node(5, "Optional: Nemotron second reader", ai ? "Looks only for values step 4 missed. Identity is removed first, every value must sit on a real line of the document, and each is marked “read by AI”." : "Looks only for values step 4 missed, with identity removed first. Off unless switched on.", "ai", "optional"),
        node(6, "You review", "Every value is shown with the line it came from. Correct a wrong one or set it aside. Only the values can be changed, never the text or the file’s details.", "you"),
        node(7, "Save", "A sealed JSON document in the document store (its own database), the values in the main database, and the file sealed on disk.", "data"),
        node(8, "Risk classes and screens", "The risk model gives a class for heart, blood sugar and blood pressure, with reasons and what is missing. Home, Outlook and the clinical view update.", "ml")] },
    ]),
    "A file goes through safety checks, then its text is read. The pattern reader finds values by name and converts units. Optionally a second reader, the Nemotron model, looks for anything missed, after identity is removed and only if each value can be proven from a line of the document. You then review and correct the values. The document is saved as a sealed JSON record, the values go to the main database, and the risk model updates your three risk classes.");
}

// ------------------------------------------------------------------ 2. the system map (SVG)
function box(x, y, w, hgt, title, sub, cls) {
  return s("g", { class: `dg ${cls}` }, s("rect", { x, y, width: w, height: hgt, rx: 12 }), s("text", { x: x + w / 2, y: y + 24, class: "dg-t", "text-anchor": "middle" }, title),
    ...sub.map((t, i) => s("text", { x: x + w / 2, y: y + 44 + i * 16, class: "dg-s", "text-anchor": "middle" }, t)));
}
const arrow = (x1, y1, x2, y2, label) => s("g", { class: "dg-a" }, s("line", { x1, y1, x2, y2, "marker-end": "url(#ah)" }), label ? s("text", { x: (x1 + x2) / 2 + 6, y: (y1 + y2) / 2 - 4, class: "dg-l" }, label) : null);

function systemMap() {
  const svg = s("svg", { viewBox: "0 0 920 560", class: "dg-svg", role: "img", "aria-labelledby": "dg-title dg-desc" },
    s("title", { id: "dg-title" }, "Where everything lives"), s("desc", { id: "dg-desc" }, "The browser talks to one server. The server uses a main database, a separate sealed document store, a risk model, a knowledge base of WHO and MedlinePlus pages, and two AI models."),
    s("defs", null, s("marker", { id: "ah", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" }, s("path", { d: "M0 0 L10 5 L0 10 z", class: "dg-head" }))),
    box(320, 14, 280, 66, "Your browser", ["Plain web page, hash routing,", "strict content security policy"], "you"),
    arrow(460, 80, 460, 128, "HTTPS, signed cookie"),
    box(260, 128, 400, 92, "PranaSync server (FastAPI)", ["Who are you? Rate limits. Upload checks.", "Pattern reader · review · safety rules · audit log"], "code"),
    arrow(330, 220, 130, 300), arrow(400, 220, 345, 300), arrow(520, 220, 555, 300), arrow(590, 220, 780, 300),
    box(20, 300, 220, 100, "Main database", ["PostgreSQL: accounts, values", "read, records, security log"], "data"),
    box(250, 300, 200, 100, "Document store", ["Its own database: one", "sealed JSON per upload"], "lock"),
    box(460, 300, 200, 100, "Risk model", ["Gradient-boosted trees +", "exact per-value reasons"], "ml"),
    box(670, 300, 230, 100, "Knowledge base", ["25 approved sources, 421", "passages: WHO, MedlinePlus"], "data"),
    arrow(540, 400, 420, 452, "facts"), arrow(580, 400, 690, 452, "facts"), arrow(790, 400, 790, 452, "passages"),
    box(260, 452, 260, 90, "Nemotron (hosted)", ["Writes plain-language text.", "Optional second document reader"], "ai"),
    box(580, 452, 320, 90, "MedGemma (this computer)", ["Writes the medical insights.", "Cites the knowledge base"], "ai"),
    s("g", { class: "dg lock-note" }, s("text", { x: 20, y: 440, class: "dg-s" }, "Sealed: AES-256-GCM,"), s("text", { x: 20, y: 456, class: "dg-s" }, "one key per person,"), s("text", { x: 20, y: 472, class: "dg-s" }, "owner or administrator only")));
  return h("div", { class: "dg-scroll" }, svg);
}

// ------------------------------------------------------------------ 3. who can open a document
function accessFlow() {
  return fig("ar-3", "Who can open a document", "A document is locked to the person it belongs to. An administrator can read, never change, and every look is logged.",
    flow("Access lock", [{ nodes: [node(1, "Someone asks", "The request carries a signed session. The person is taken from it, never from the address or anything typed.", "you"),
      node(2, "The rule", "Your own document: yes. Someone else’s: only an administrator, and only to read. Anything else looks exactly like “not found”.", "code"),
      node(3, "Unseal", "The document is sealed with a key made for that person alone, bound to the document’s id, so a copied row opens nowhere else.", "data"),
      node(4, "Shown, and logged if an administrator", "Administrator reads and refusals are written to the audit log with who looked at whose document.", "code")] }]),
    "The server takes the person from the signed session. The owner may open and change their documents. An administrator may open anyone’s documents to read but not change. Everyone else is told the document was not found. The stored JSON is sealed with a key unique to the owner, so copying the database file reveals nothing, and every administrator read is written to the audit log.");
}

// ------------------------------------------------------------------ 4. every AI answer is checked
function aiFlow() {
  return fig("ar-4", "Every AI answer passes the safeguard rails before you see it", "The model writes words. Code does the numbers and decides whether the words may be shown.",
    flow("AI answer checks", [{ nodes: [node(1, "Facts computed by code", "Your values, classes, trends and what is missing. No model has touched them.", "code"),
      node(2, "Approved documents found", "The most relevant WHO and MedlinePlus passages for these facts, so the model has something to cite.", "data"),
      node(3, "The model writes", "Nemotron for the plain-language text, MedGemma for the medical insights. Key values and words are marked for highlighting.", "ai"),
      node(4, "Safeguard rails", "Every number must be in the facts. No diagnosis, medicine advice, percentage chance, forecast, fear or links. Hidden orders in a document are removed first. Thirteen numbered rails, tested against attacks.", "code")] },
    { nodes: [node(5, "Passes", "Shown with an “AI-written” label, with the sources it used.", "you"), node(6, "Fails", "Thrown away. You see the computed numbers and a plain reason instead of a wrong answer.", "you")] }]),
    "Code computes the facts. The approved WHO and MedlinePlus passages that match are found. A model writes the text. Code then checks every number against the facts and blocks diagnosis wording and medicine advice. If a check fails, the text is discarded and the computed numbers are shown instead.");
}

// ------------------------------------------------------------------ 5. which reader is best
function bestTable(ex) {
  const r = ex?.results;
  if (!r?.all) return h("p", { class: "note" }, "The reader comparison has not been run yet. Run python scripts/eval_extraction.py to measure it.");
  const rows = [];
  const add = (kind, name, m) => m && rows.push([kind, name, pct(m.recall), pct(m.precision), pct(m.f1), String(m.invented)]);
  add("Easy layouts", "Pattern reader", r.easy?.patterns); add("Easy layouts", "Pattern reader + Nemotron", r.easy?.patterns_plus_nemotron);
  add("Unusual layouts", "Pattern reader", r.hard?.patterns); add("Unusual layouts", "Pattern reader + Nemotron", r.hard?.patterns_plus_nemotron);
  add("All", "Pattern reader", r.all.patterns); add("All", "Pattern reader + Nemotron", r.all.patterns_plus_nemotron);
  const n = ex.nemotron;
  return h("div", null,
    h("div", { class: "tscroll" }, h("table", { class: "mt ct-table" }, h("caption", null, `Made-up documents with known answers (${ex.documents_per_kind} of each kind)`),
      h("thead", null, h("tr", null, ["Documents", "Reader", "Recall", "Precision", "F1", "Invented values"].map((t, i) => h("th", { scope: "col", class: i > 1 ? "mt-num" : "" }, t)))),
      h("tbody", null, rows.map((x) => h("tr", null, x.map((c, i) => (i === 0 ? h("th", { scope: "row" }, c) : h("td", { class: i > 1 ? "mt-num" : "" }, c)))))))),
    ex.decision ? h("p", { class: "ar-decision" }, h("b", null, "Decision: "), ex.decision) : null,
    n ? h("p", { class: "fine" }, `Nemotron was asked ${n.calls} times (${n.failed_calls} unavailable); median ${n.median_seconds} s, slowest ${n.slowest_seconds} s per document. The pattern reader takes a few milliseconds.`) : null);
}

function bestFlow(ex) {
  return fig("ar-5", "How we decide which reader is best", "Four measures, borrowed from how medical-insight benchmarks are judged, plus the one that matters most when the output is a number in someone’s record.",
    h("div", null,
      h("ul", { class: "ar-crit" }, [["Recall", "How many of the true values it found."], ["Precision", "How many of the values it returned are right."], ["F1", "The balance of the two."], ["Invented values", "A number returned that is not the true one. This must stay at zero."]]
        .map(([t, d]) => h("li", null, h("b", null, t), h("span", null, d)))),
      bestTable(ex),
      h("p", { class: "fine" }, "Novelty, which benchmarks use for new clinical insights, has no meaning for reading a number off a page, so it is not scored. The human check is the review page: you confirm every value before it is trusted. Practice documents are made up, so this shows the method works, not that every real document will read perfectly.")));
}

export async function architectureView() {
  let ex = null;
  try { ex = (await api("models")).extraction; } catch { /* the diagrams do not need it */ }
  return h("div", { class: "arch" }, uploadFlow(ex),
    fig("ar-2", "Where everything lives", "One server, two databases, a trained model, a knowledge base and two AI models. The document store is separate from the main database and sealed.", systemMap(),
      "The browser connects to one server over HTTPS with a signed cookie. The server uses the main PostgreSQL database for accounts and values, a separate sealed document store for the JSON of each upload, a risk model, and a knowledge base of approved WHO and MedlinePlus passages. Two AI models write text: Nemotron, hosted, and MedGemma, which runs on this computer."),
    accessFlow(), aiFlow(), bestFlow(ex));
}
