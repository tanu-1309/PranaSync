// Administrators only: who has documents, their list, and any one document as it is stored (read-only). The server checks the role on every request and logs every look.
import { h, api, clear } from "./ui.js";
import { pagehead } from "./record.js";

const when = (iso) => { try { return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }); } catch { return iso || "—"; } };

export async function adminView(me) {
  if (!me.admin) return h("div", { class: "page" }, pagehead("Administration", null), h("p", { class: "note" }, "This page is for administrators."));
  const people = h("div", { class: "ad-people" }), docs = h("div", { class: "ad-docs" }), view = h("div", { class: "ad-view", "aria-live": "polite" });
  async function showDoc(pid, id) {
    clear(view); view.append(h("p", { class: "faint" }, "Opening…"));
    try {
      const r = await api(`admin/people/${encodeURIComponent(pid)}/documents/${encodeURIComponent(id)}`, { fresh: true });
      clear(view); view.append(h("h3", null, "The stored document (read-only)"), h("pre", { tabindex: "0" }, JSON.stringify(r.document, null, 2)));
    } catch (ex) { clear(view); view.append(h("p", { class: "err", role: "alert" }, ex.message)); }
  }
  async function showPerson(pid) {
    clear(docs); clear(view); docs.append(h("h3", null, `Documents of ${pid}`));
    try {
      const r = await api(`admin/people/${encodeURIComponent(pid)}/documents`, { fresh: true });
      docs.append(h("ul", { class: "ad-list" }, r.documents.map((d) => h("li", null, h("button", { class: "btn sm", type: "button", onclick: () => showDoc(pid, d.doc_id) }, "Open"), h("b", null, ` ${d.filename} `),
        h("small", { class: "faint" }, `${d.status === "confirmed" ? "checked" : "not checked"} · ${d.values} values · ${when(d.uploaded_at)}`)))));
    } catch (ex) { docs.append(h("p", { class: "err", role: "alert" }, ex.message)); }
  }
  try {
    const r = await api("admin/people", { fresh: true });
    people.append(h("h3", null, "People with documents"), r.people.length
      ? h("ul", { class: "ad-list" }, r.people.map((p) => h("li", null, h("button", { class: "btn sm", type: "button", onclick: () => showPerson(p.patient_id) }, "Show documents"), h("b", null, ` ${p.patient_id} `),
        h("small", { class: "faint" }, `${p.documents} document${p.documents === 1 ? "" : "s"} · last ${when(p.last_upload)}`))))
      : h("p", { class: "note" }, "No documents have been uploaded yet."));
  } catch (ex) { people.append(h("p", { class: "err", role: "alert" }, ex.message)); }
  return h("div", { class: "page admin" }, pagehead("Administration", "Read-only access to the document store. Every document you open is written to the audit log with your ID."), people, docs, view);
}
