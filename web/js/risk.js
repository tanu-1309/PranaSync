// Risk on the screen: three areas, each with a class (never a percentage), the parameters behind it, how much evidence it rests on, and what is missing.
// Also the upload page, where a person adds documents one at a time and watches the picture grow.
import { h, icon, api, clear, fmtDate, forgetCache } from "./ui.js";
import { pagehead } from "./record.js";
import { startSteps, yourValues, whatWouldHelp, urgentBox, historyAsync } from "./homeparts.js";

const TONE = { lower: "teal", moderate: "gold", higher: "ember", unknown: "slate" };
const MEANING = {
  lower: "Your measurements look like those of people without this condition.",
  moderate: "Some of your measurements look like those of people who have this condition. Worth a conversation.",
  higher: "Many of your measurements look like those of people who have this condition. Please raise it with your doctor.",
  unknown: "We need a document with these values before we can say anything.",
};
const ARROW = { raises: "▲", lowers: "▼" };

export function evidenceBar(a) {
  return h("div", { class: "rk-ev", title: "How much of what the model looks at your documents supply. It is not a chance of being right." },
    h("div", { class: "rk-evl" }, h("span", null, "Evidence strength"), h("b", null, `${a.evidence}`, h("small", null, " / 100")), h("em", null, a.evidence_text)),
    h("div", { class: "rk-bar", role: "img", "aria-label": `Evidence strength ${a.evidence} out of 100` }, h("i", { style: { width: `${Math.max(3, a.evidence)}%` } })));
}

function drivers(a, max) {
  if (!a.drivers.length) return null;
  return h("ul", { class: "rk-drv" }, a.drivers.slice(0, max).map((d) => h("li", { class: d.direction },
    h("span", { class: "ar", "aria-hidden": "true" }, ARROW[d.direction]), h("b", null, d.label), h("span", { class: "v" }, d.value),
    h("span", { class: "s" }, `${d.direction === "raises" ? "pushes it up" : "pushes it down"}, ${d.strength}`))));
}

export function riskCard(a, { full = false } = {}) {
  const tone = TONE[a.level];
  const unknown = a.level === "unknown";
  return h("article", { class: `rk-card tone-${tone}` },
    h("h3", { class: "gk" }, a.label),
    h("b", { class: "rk-class" }, h("span", { class: "sr" }, `${a.label}: `), a.level_text),
    h("p", { class: "rk-mean" }, MEANING[a.level]),
    evidenceBar(a),
    unknown ? h("p", { class: "rk-note" }, "Add a document with these values and a class will appear.") : h("div", null, h("h4", null, "What is behind it"), drivers(a, full ? 6 : 3)),
    a.missing.length ? h("p", { class: "rk-miss" }, h("b", null, "Missing: "), a.missing.slice(0, full ? 8 : 4).map((m) => m.label).join(", "), a.missing.length > (full ? 8 : 4) ? "…" : "") : h("p", { class: "rk-miss ok" }, "Nothing important is missing."));
}

export function missingBox(risk) {
  const ups = risk.next_uploads || [];
  const hasMissing = (risk.missing || []).length;
  return h("section", { class: "rk-box" },
    h("div", null,
      h("h3", null, hasMissing ? "Missing parameters" : "All the main parameters are in"),
      hasMissing ? h("p", null, "These would make the three estimates stronger: ", h("b", null, risk.missing.slice(0, 10).map((m) => m.label).join(", ")), risk.missing.length > 10 ? "…" : "", ".") : h("p", null, "Add newer documents any time and the picture updates."),
      ups.length ? h("p", { class: "rk-next" }, "Most useful to upload next: ", h("b", null, ups.slice(0, 2).map((u) => u.help).join("; or "))) : null),
    h("a", { class: "btn solid", href: "#/upload" }, "Upload a document"));
}

function shell(root, risk) {
  clear(root);
  if (!risk.available) { root.append(h("p", { class: "note" }, risk.reason || "The risk model is not available.")); return; }
  root.append(h("div", { class: "rk-grid" }, risk.areas.map((a) => riskCard(a))), missingBox(risk),
    h("p", { class: "fine" }, risk.caveat, " No percentages are shown: the data the model learned from has no follow-up outcomes, so a percentage would claim more than it can support."));
}

// "Your health at a glance" on Home: the three classes, their parameters and evidence strength, and what is missing.
export function glanceRisk() {
  const root = h("div", { class: "rk-root" }, h("div", { class: "rk-grid" }, [1, 2, 3].map(() => h("div", { class: "rk-card skel" }))));
  api("risk", { fresh: true }).then((r) => shell(root, r)).catch(() => { clear(root); root.append(h("p", { class: "note" }, "The risk estimates could not be loaded. Please try again.")); });
  return h("section", { class: "glance", id: "glance", tabindex: "-1", "aria-labelledby": "glance-h" }, h("h2", { id: "glance-h" }, "Your health at a glance"),
    h("p", { class: "standfirst" }, "Three areas. Each shows where you sit (lower, moderate or higher), the reasons, and how much information the answer rests on. These are not diagnoses and not chances."), root);
}

// Outlook: the same three areas in full (up to six parameters each).
export function outlookRisk() {
  const root = h("div", { class: "rk-root" }, h("div", { class: "rk-grid" }, [1, 2, 3].map(() => h("div", { class: "rk-card skel" }))));
  api("risk", { fresh: true }).then((r) => {
    clear(root);
    if (!r.available) { root.append(h("p", { class: "note" }, r.reason)); return; }
    root.append(h("div", { class: "rk-grid" }, r.areas.map((a) => riskCard(a, { full: true }))), missingBox(r), h("p", { class: "fine" }, r.caveat));
  }).catch(() => { clear(root); root.append(h("p", { class: "note" }, "The risk estimates could not be loaded.")); });
  return h("section", { class: "outlook-sec" }, h("h2", null, "Your health risks"),
    h("p", { class: "standfirst" }, "A class for each area, with the reasons. We don’t show a probability: there isn’t enough backing to prove one."), root);
}

// ------------------------------------------------------------------------------------------ home for people who registered and upload their own documents
export function uploadsHome(me) {
  const host = h("div", { class: "hp-host" });
  api("risk", { fresh: true }).then((r) => {
    clear(host);
    if (!r.available) return;
    host.append(r.documents ? yourValues(r) : startSteps(), r.documents ? historyAsync() : null, whatWouldHelp({ scenarios: [] }, r));
  }).catch(() => {});
  return h("div", { class: "page home" },
    pagehead(`Welcome${me.name && me.name !== me.id ? ", " + me.name : ""}`, "Your picture builds up as you add documents, one at a time."),
    h("p", { class: "note" }, "Your ID is ", h("b", null, me.id), ". Write it down: you need it, with your password, to sign in again."), glanceRisk(), host, urgentBox());
}

// ------------------------------------------------------------------------------------------ upload page
export function uploadView(me) {
  const out = h("div", { class: "up-out", "aria-live": "polite" });
  const list = h("div", { class: "up-list" });
  const riskRoot = h("div", { class: "rk-root" });
  let meta = { can_upload: true, supported: [], max_mb: 10 };

  const input = h("input", { type: "file", id: "up-file", accept: ".pdf,.docx,.txt,.md,.csv,.xlsx,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp", hidden: true });
  const drop = h("label", { class: "up-drop", for: "up-file", tabindex: "0" },
    icon("upload", 24), h("b", null, "Choose a document or drop it here"), h("span", null, "PDF, Word, text, CSV, Excel, or a photo or scan of a report. Up to 10 MB. Photos are read on this computer and every value is marked for you to check."),
    h("small", { class: "up-privacy" }, "Your file is stored sealed, for your account only. It is read on this computer. If the optional AI second reader is switched on, it sees only lines with numbers, with names, dates of birth, addresses, phone numbers and IDs removed first."));

  async function send(file) {
    clear(out);
    out.append(h("p", { class: "up-busy" }, h("i", { class: "spin" }), ` Reading ${file.name}…`));
    const fd = new FormData(); fd.append("file", file);
    try {
      const r = await api("documents", { method: "POST", body: fd });
      forgetCache();
      location.hash = `#/review/${r.document.id}`;           // always review what was read before moving on
      return;

    } catch (ex) { clear(out); out.append(h("p", { class: "err", role: "alert" }, icon("info", 16), ex.message)); }
  }
  input.addEventListener("change", () => { if (input.files[0]) send(input.files[0]); input.value = ""; });
  ["dragover", "dragenter"].forEach((e) => drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.add("on"); }));
  ["dragleave", "drop"].forEach((e) => drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.remove("on"); }));
  drop.addEventListener("drop", (ev) => { const f = ev.dataTransfer?.files?.[0]; if (f) send(f); });
  drop.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); input.click(); } });

  async function refresh() {
    try {
      const d = await api("documents", { fresh: true }); meta = d;
      clear(list);
      list.append(h("h3", null, `Your documents (${d.documents.length})`));
      if (!d.documents.length) list.append(h("p", { class: "note" }, me.guest ? "Guest mode shows a sample record, so there are no uploads." : "Nothing uploaded yet."));
      d.documents.forEach((x) => list.append(h("div", { class: "up-row" }, h("div", null, h("b", null, x.filename), h("small", null, `${x.kind || "document"} · ${x.n_values} values · ${x.uploaded_at ? fmtDate(x.uploaded_at.slice(0, 10)) : ""}`), h("span", { class: `rv-chip ${x.status === "confirmed" ? "ok" : "todo"}` }, x.status === "confirmed" ? "Checked by you" : "Needs your check")),
        h("a", { class: "btn sm", href: `#/review/${x.id}` }, x.status === "confirmed" ? "View or correct values" : "Review values"),
        d.can_upload ? h("button", { class: "btn ghost sm", type: "button", onclick: async () => {
          if (!confirm(`Delete ${x.filename} and the values read from it?`)) return;
          try { const r = await api(`documents/${x.id}`, { method: "DELETE" }); shell(riskRoot, r.risk); clear(out); refresh(); } catch (ex) { alert(ex.message); }
        } }, "Delete") : null)));
    } catch { /* leave the list as it is */ }
  }
  refresh();
  api("risk", { fresh: true }).then((r) => shell(riskRoot, r)).catch(() => {});

  const body = me.guest ? h("p", { class: "note" }, "Uploading is switched off in guest mode. Create an account to add your own documents.") : [drop, input, out];
  return h("div", { class: "page upload" },
    pagehead("Upload documents", "Add one document at a time: a lab report, a clinic visit note, a tracker export. We read the values, and the three estimates update."),
    body, h("h2", { class: "up-h" }, "Where this stands"), riskRoot, list,
    h("p", { class: "fine" }, "Documents are read on the server and kept only for your account. We store the values we read, with the line they came from, so each number can be traced and removed with its document."));
}
