// Review a document right after it is read. The whole page is about one thing: check the values we took from the document and correct any that are wrong.
// Only those values can be changed (or set aside). The file's details, the times and the extracted text are shown but never editable.
import { h, api, icon, clear, forgetCache } from "./ui.js";
import { pagehead } from "./record.js";

const when = (iso) => { try { return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }); } catch { return iso || "—"; } };
const size = (n) => (n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : n >= 1024 ? `${Math.round(n / 1024)} KB` : `${n} bytes`);

function metaCard(d) {
  const row = (k, v) => [h("dt", null, k), h("dd", null, v)];
  const st = d.status === "confirmed" ? h("span", { class: "rv-chip ok" }, "Checked by you") : h("span", { class: "rv-chip todo" }, "Needs your check");
  return h("section", { class: "rv-meta", "aria-label": "About this document" }, h("dl", null,
    row("File", h("b", null, d.source.filename)), row("Uploaded", when(d.uploaded_at)), row("Text read", when(d.extracted_at)),
    row("Checked", d.reviewed_at ? when(d.reviewed_at) : "Not yet"), row("Type and size", `${d.source.type.toUpperCase()} · ${size(d.source.size_bytes)}`), row("Read with", d.extraction?.method || "patterns"), row("Status", st)));
}

function valueRow(v, ctl, can) {
  const id = `rv-${v.param}`;
  let input;
  if (v.kind === "choice") {
    input = h("select", { id, disabled: !can || null, "aria-describedby": `${id}-e` }, v.choices.map((c) => h("option", { value: String(c.value), selected: c.value === v.value || null }, c.label)));
  } else {
    input = h("input", { id, type: "number", step: "any", min: String(v.min), max: String(v.max), value: String(v.value), disabled: !can || null, inputmode: "decimal", "aria-describedby": `${id}-e` });
  }
  const ign = h("input", { id: `${id}-i`, type: "checkbox", checked: v.ignored || null, disabled: !can || null });
  const err = h("small", { id: `${id}-e`, class: "rv-err", role: "alert" });
  const tr = h("tr", { class: v.ignored ? "off" : "" },
    h("th", { scope: "row" }, h("label", { for: id }, v.label), v.read_by === "AI" ? h("span", { class: "rv-ai" }, "Read by AI: please check") : v.read_by === "image" ? h("span", { class: "rv-ai" }, "Read from an image: please check") : null, h("small", { class: "rv-orig" }, `Read as ${v.choices.length ? v.choices.find((c) => c.value === v.original_value)?.label ?? v.original_value : `${v.original_value}${v.unit ? " " + v.unit : ""}`}`)),
    h("td", { class: "rv-in", "data-label": "Value to use" }, h("div", { class: "rv-inwrap" }, input, v.unit ? h("span", { class: "rv-unit" }, v.unit) : null), err),
    h("td", { class: "rv-src", "data-label": "Found in the document as" }, v.source_text ? h("q", null, v.source_text) : h("span", { class: "faint" }, "—")),
    h("td", { class: "rv-use", "data-label": "Use it?" }, h("label", { class: "rv-ign" }, ign, h("span", null, "Don’t use this value"))));
  ctl[v.param] = { input, ign, err, tr, v };
  const upd = () => { tr.classList.toggle("off", ign.checked); tr.classList.toggle("changed", changedRow(ctl[v.param])); };
  input.addEventListener("input", upd); ign.addEventListener("change", upd);
  return tr;
}
const numOf = (c) => (c.input.value === "" ? null : Number(c.input.value));
const changedRow = (c) => numOf(c) !== c.v.value || c.ign.checked !== c.v.ignored;

export async function reviewView(me, docId) {
  let r;
  try { r = await api(`documents/${encodeURIComponent(docId)}`, { fresh: true }); }
  catch (ex) { return h("div", { class: "page" }, pagehead("Review document", null), h("p", { class: "err", role: "alert" }, icon("info", 16), ex.message || "That document could not be opened."), h("a", { class: "btn", href: "#/upload" }, "Go to your documents")); }
  const d = r.document, can = r.can_edit;
  const ctl = {}, msg = h("div", { class: "rv-msg", role: "status", "aria-live": "polite" });
  const body = h("tbody", null, d.values.map((v) => valueRow(v, ctl, can)));
  const save = h("button", { class: "btn solid", type: "submit" }, d.status === "confirmed" ? "Save changes" : "Save and confirm these values");
  const reset = h("button", { class: "btn ghost", type: "button", onclick: () => { Object.values(ctl).forEach((c) => { c.input.value = String(c.v.original_value); c.ign.checked = false; c.tr.classList.remove("off", "changed"); }); } }, "Put back what was read");
  const bar = h("div", { class: "rv-actions" }, save, reset, h("span", { class: "fine" }, "Your risk classes already use these values. Saving updates them."));
  const form = h("form", { class: "rv-form", novalidate: true, onsubmit: async (e) => {
    e.preventDefault(); msg.replaceChildren(); msg.className = "rv-msg";
    Object.values(ctl).forEach((c) => c.err.replaceChildren());
    const edits = Object.fromEntries(Object.entries(ctl).map(([p, c]) => [p, { value: numOf(c), ignore: c.ign.checked }]));
    save.disabled = true; save.textContent = "Saving…";
    try {
      const out = await api(`documents/${encodeURIComponent(docId)}/values`, { method: "PUT", body: { edits } });
      forgetCache();
      msg.className = "rv-msg ok";
      msg.replaceChildren(icon("info", 16), h("span", null, "Saved. Your risk classes are updated. "), h("a", { href: "#/" }, "See them on Home"), " · ", h("a", { href: "#/upload" }, "Back to your documents"));
      Object.values(ctl).forEach((c) => { const nv = out.document.values.find((x) => x.param === c.v.param); if (nv) { c.v = nv; c.tr.classList.remove("changed"); c.tr.querySelector(".rv-orig").textContent = `Read as ${nv.choices.length ? nv.choices.find((x) => x.value === nv.original_value)?.label ?? nv.original_value : `${nv.original_value}${nv.unit ? " " + nv.unit : ""}`}`; } });
      document.querySelector(".rv-chip")?.replaceChildren("Checked by you"); document.querySelector(".rv-chip")?.setAttribute("class", "rv-chip ok");
      historyBox(out.document);
    } catch (ex) { msg.className = "rv-msg err"; msg.replaceChildren(icon("info", 16), ex.message); }
    save.disabled = false; save.textContent = "Save changes";
  } },
    h("div", { class: "tscroll" }, h("table", { class: "rv-table" }, h("caption", { class: "sr" }, "Values read from the document"),
      h("thead", null, h("tr", null, ["Value", "Value to use", "Found in the document as", "Use it?"].map((t) => h("th", { scope: "col" }, t)))), body)),
    can ? bar : h("p", { class: "note" }, "This is a read-only view."), msg);
  const hist = h("div");
  const historyBox = (doc) => { clear(hist); if (!doc.edit_history.length) return; hist.append(h("details", { class: "why" }, h("summary", null, `Changes you made (${doc.edit_history.length})`),
    h("ul", { class: "list-x" }, doc.edit_history.slice().reverse().map((x) => h("li", null, h("b", null, x.label), `: ${x.from} → ${x.to} `, h("small", { class: "faint" }, when(x.at))))))); };
  historyBox(d);
  const ext = ("." + (d.source?.type || "")).toLowerCase(), isImg = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"].includes(ext);
  const fileUrl = `/api/documents/${encodeURIComponent(docId)}/file`;
  const original = h("aside", { class: "rv-original", "aria-label": "The original document" },
    h("h2", null, "The original"),
    isImg ? h("a", { href: fileUrl, target: "_blank", rel: "noopener" }, h("img", { src: fileUrl, alt: "The document you uploaded", loading: "lazy" })) : null,
    h("a", { class: "btn", href: fileUrl, target: "_blank", rel: "noopener" }, ext === ".pdf" || isImg ? "Open the original in a new tab" : "Download the original"),
    h("p", { class: "fine" }, "Check each value on the left against this. The text we read from it is below."));
  return h("div", { class: "page review" },
    pagehead("Review the document", "We read these values from your document. Check them against the original and correct any that are wrong. Only these values can be changed."),
    metaCard(d), d.notes.length ? h("p", { class: "note" }, d.notes.join(" ")) : null, h("div", { class: "rv-split" }, form, original), hist,
    h("details", { class: "why rv-text" }, h("summary", null, "The text we extracted (read-only)"), h("pre", { tabindex: "0", "aria-label": "Extracted text" }, d.extracted_text || "No text was stored for this document.")));
}
