// Account. One page, four sections, and a side list so you can jump to any of them: Your details (editable), Sign-in and security, Your data, What we keep.
// A summary at the top answers the first questions: who is signed in, how complete the details are, and the three things people most often come here to do.
import { h, api, icon, forgetCache } from "./ui.js";
import { pagehead } from "./record.js";
import { codesPanel } from "./codes.js";

const SOURCE = { you: "Entered by you", record: "From your health record", empty: "Not provided yet" };
const HINT = { age: "Used in your risk classes.", sex: "Used in your risk classes.", height: "In centimetres.", allergies: "Medicines, foods or anything you react to.", family: "Conditions that run in your family.",
  email: "Optional. Never used to sign in.", phone: "Optional.", emergency: "Optional. Name and phone number." };
const SECTIONS = [["ac-details", "Your details"], ["ac-security", "Sign-in and security"], ["ac-data", "Your data"], ["ac-privacy", "What we keep"]];
const calm = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

function goTo(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.scrollIntoView({ behavior: calm() ? "auto" : "smooth", block: "start" });
  el.focus({ preventScroll: true });
}
const jump = (id) => (e) => { e.preventDefault(); goTo(id); };

function block(id, title, lead, ...kids) {
  return h("section", { class: "ac-block", id, tabindex: "-1", "aria-labelledby": `${id}-h` }, h("h2", { id: `${id}-h` }, title), lead ? h("p", { class: "ac-lead" }, lead) : null, ...kids);
}

// ------------------------------------------------------------------ summary at the top
function summary(p, state) {
  const kind = p.guest ? "Sample record (guest)" : p.mode === "uploads" ? "Account built from your documents" : "Health record account";
  const copy = h("button", { class: "btn ghost sm", type: "button", onclick: async () => {
    try { await navigator.clipboard.writeText(p.id); copy.textContent = "ID copied"; } catch { copy.textContent = "Select and copy the ID"; }
    setTimeout(() => { copy.textContent = "Copy my ID"; }, 2500);
  } }, "Copy my ID");
  const meter = h("div", { class: "ac-meter", role: "img", "aria-label": "Details filled in" }, h("i"));
  const text = h("span", { class: "ac-comp-t" }, "Loading your details…");
  const todo = h("a", { href: "#/account", class: "ac-comp-a", hidden: true }, "Fill in the rest");
  state.nameEl = h("h2", { class: "ac-name", id: "ac-who" }, p.guest ? "Sample record" : p.id);
  state.onProfile = (d) => {
    const keys = Object.keys(d.values), filled = keys.filter((k) => d.source[k] !== "empty").length;
    meter.firstChild.style.width = `${Math.round((filled / keys.length) * 100)}%`;
    meter.setAttribute("aria-label", `${filled} of ${keys.length} details filled in`);
    text.textContent = `${filled} of ${keys.length} details filled in`;
    const firstEmpty = keys.find((k) => d.source[k] === "empty");
    todo.hidden = !firstEmpty || !d.can_edit;
    todo.onclick = (e) => { e.preventDefault(); goTo("ac-details"); document.getElementById(`pf-${firstEmpty}`)?.focus({ preventScroll: true }); };
    state.nameEl.textContent = d.values.name || (p.guest ? "Sample record" : p.id);
  };
  return h("section", { class: "ac-summary", "aria-labelledby": "ac-who" },
    h("span", { class: "ac-avatar", "aria-hidden": "true" }, p.guest ? "G" : p.id.slice(-2)),
    h("div", { class: "ac-who" }, state.nameEl, h("p", null, h("span", { class: "chip-kind" }, kind), " ID ", h("b", { class: "mono" }, p.id), " ", p.guest ? null : copy)),
    h("div", { class: "ac-comp" }, meter, text, todo),
    h("div", { class: "ac-quick", role: "group", "aria-label": "Quick actions" },
      h("a", { class: "btn", href: "#/account", onclick: jump("ac-details") }, "Edit my details"),
      h("a", { class: "btn", href: "#/account", onclick: jump("ac-security") }, "Change my password"),
      h("a", { class: "btn", href: "#/account", onclick: jump("ac-data") }, "Download my data")));
}

// ------------------------------------------------------------------ 1. your details
function detailsBlock(p, state, onSaved) {
  const root = h("div");
  api("profile", { fresh: true }).then((d) => draw(d)).catch(() => root.append(h("p", { class: "note" }, "Your details could not be loaded. Please try again.")));

  function draw(d) {
    state.onProfile?.(d);
    root.replaceChildren();
    const inputs = {}, start = { ...d.values };
    const dirty = () => Object.keys(inputs).some((k) => String(inputs[k].value) !== String(start[k] ?? ""));
    const field = (k, wide) => {
      const f = d.fields[k], id = `pf-${k}`, val = d.values[k] ?? "";
      let el;
      if (f.choices) el = h("select", { id, name: k, disabled: !d.can_edit || null, "aria-describedby": `${id}-s` }, h("option", { value: "" }, "Choose…"), f.choices.map((c) => h("option", { value: c, selected: c === val || null }, c)));
      else if (k === "allergies" || k === "family") el = h("textarea", { id, name: k, rows: "2", maxlength: String(f.max), disabled: !d.can_edit || null, "aria-describedby": `${id}-s` }, String(val));
      else {
        const type = f.kind === "email" ? "email" : f.kind === "phone" ? "tel" : f.kind === "int" ? "number" : "text";
        el = h("input", { id, name: k, type, maxlength: String(f.max + 1), value: String(val), disabled: !d.can_edit || null, "aria-describedby": `${id}-s`,
          autocomplete: { name: "name", email: "email", phone: "tel" }[k] || "off", inputmode: f.kind === "int" ? "numeric" : null, min: f.kind === "int" ? "0" : null });
      }
      inputs[k] = el;
      return h("div", { class: `ac-field${wide ? " wide" : ""}` }, h("label", { for: id }, f.label), el,
        h("small", { id: `${id}-s`, class: `src-${d.source[k]}` }, h("b", null, SOURCE[d.source[k]]), HINT[k] ? ` · ${HINT[k]}` : ""));
    };
    const msg = h("div", { class: "ac-msg", role: "status", "aria-live": "polite" });
    const save = h("button", { class: "btn solid", type: "submit" }, "Save changes");
    const discard = h("button", { class: "btn ghost", type: "button", onclick: () => draw(d) }, "Discard changes");
    const bar = h("div", { class: "ac-savebar", hidden: true }, h("span", null, "You have unsaved changes."), h("div", null, discard, save));
    const form = h("form", { class: "ac-form", novalidate: true, onsubmit: async (e) => {
      e.preventDefault(); msg.replaceChildren(); msg.className = "ac-msg";
      const values = Object.fromEntries(Object.entries(inputs).map(([k, el]) => [k, el.value]));
      save.disabled = true; save.textContent = "Saving…";
      try {
        const r = await api("profile", { method: "PUT", body: { values } });
        forgetCache(); onSaved?.();
        draw(r);
        const ok = root.querySelector(".ac-msg");
        if (ok) { ok.className = "ac-msg ok"; ok.replaceChildren(icon("info", 16), "Saved. Your details are updated everywhere in the portal."); }
      } catch (ex) { msg.className = "ac-msg err"; msg.replaceChildren(icon("info", 16), ex.message); save.disabled = false; save.textContent = "Save changes"; }
    } },
      h("fieldset", null, h("legend", null, "About you"), h("div", { class: "ac-grid" }, field("name"), field("age"), field("sex"), field("blood"), field("height"))),
      h("fieldset", null, h("legend", null, "Health background"), h("div", { class: "ac-grid" }, field("allergies", true), field("family", true))),
      h("fieldset", null, h("legend", null, "Contact (optional)"), h("div", { class: "ac-grid" }, field("email"), field("phone"), field("emergency", true))),
      d.can_edit ? bar : h("p", { class: "note" }, "This is a sample record, so details can be seen but not changed. Create an account to keep your own."), msg);
    form.addEventListener("input", () => { bar.hidden = !dirty(); });
    form.addEventListener("change", () => { bar.hidden = !dirty(); });
    root.append(form);
  }
  return block("ac-details", "Your details", "Everything personal we hold about you. Each field says where it came from. Correct anything that is wrong.", root);
}

// ------------------------------------------------------------------ 2. sign-in and security
function recoveryFold(p) {
  const out = h("div", { class: "rc-slot" });
  const pw = h("input", { id: "rc-cur", type: "password", autocomplete: "current-password", required: true, maxlength: "200" });
  const msg = h("div", { class: "ac-msg", role: "alert", "aria-live": "polite" }), left = h("b", null, "…");
  api("recovery-codes", { fresh: true }).then((r) => { left.textContent = String(r.codes_left); }).catch(() => { left.textContent = "an unknown number of"; });
  const go = h("button", { class: "btn", type: "submit" }, "Make a new set");
  const form = h("form", { class: "ac-form", novalidate: true, onsubmit: async (e) => {
    e.preventDefault(); msg.replaceChildren(); msg.className = "ac-msg"; go.disabled = true;
    try {
      const r = await api("recovery-codes", { method: "POST", body: { current: pw.value } }); pw.value = ""; form.hidden = true;
      out.replaceChildren(codesPanel(p.id, r.recovery_codes, { doneLabel: "Done", title: "Your new recovery codes", onDone: () => { out.replaceChildren(); form.hidden = false; left.textContent = "8"; } }));
    } catch (ex) { msg.className = "ac-msg err"; msg.append(icon("info", 16), ex.message); }
    go.disabled = false;
  } }, h("div", { class: "ac-field" }, h("label", { for: "rc-cur" }, "Current password"), pw), msg, go);
  return h("details", { class: "ac-fold" }, h("summary", null, "Recovery codes"),
    h("p", null, "If you lose your password, one of these one-time codes lets you choose a new one. You have ", left, " unused. A new set replaces the old one."), form, out);
}

function deleteFold() {
  const pw = h("input", { id: "del-pw", type: "password", autocomplete: "current-password", required: true, maxlength: "200" });
  const word = h("input", { id: "del-word", autocomplete: "off", spellcheck: "false", placeholder: "DELETE" });
  const msg = h("div", { class: "ac-msg", role: "alert", "aria-live": "polite" }), go = h("button", { class: "btn danger", type: "submit" }, "Delete my account");
  const form = h("form", { class: "ac-form", novalidate: true, onsubmit: async (e) => {
    e.preventDefault(); msg.replaceChildren(); msg.className = "ac-msg";
    if (word.value.trim().toUpperCase() !== "DELETE") { msg.className = "ac-msg err"; msg.append("Type DELETE to confirm."); return; }
    if (!confirm("Delete your account and everything you uploaded? This cannot be undone.")) return;
    go.disabled = true;
    try { await api("account", { method: "DELETE", body: { current: pw.value, confirm: word.value } }); location.hash = ""; location.reload(); }
    catch (ex) { msg.className = "ac-msg err"; msg.append(icon("info", 16), ex.message); go.disabled = false; }
  } }, h("div", { class: "ac-field" }, h("label", { for: "del-pw" }, "Current password"), pw), h("div", { class: "ac-field" }, h("label", { for: "del-word" }, "Type DELETE to confirm"), word), msg, go);
  return h("details", { class: "ac-fold" }, h("summary", null, "Delete my account"),
    h("p", null, "This removes your sign-in, your details, every document you uploaded (the files and the sealed copies) and every value read from them. It cannot be undone. A person from the care team's own records keeps the team's record, but loses the sign-in and everything uploaded here."), form);
}

function securityBlock(p) {
  const field = (id, auto) => h("input", { id, type: "password", autocomplete: auto, required: true, maxlength: "200" });
  const cur = field("cur", "current-password"), nw = field("new", "new-password"), again = field("again", "new-password");
  const msg = h("div", { class: "ac-msg", role: "alert", "aria-live": "polite" }), go = h("button", { class: "btn solid", type: "submit" }, "Change password");
  const meter = h("div", { class: "meter", "aria-hidden": "true" }, h("i"));
  nw.addEventListener("input", () => {
    const v = nw.value, score = Math.min(4, (v.length >= 10) + (v.length >= 14) + (/[A-Z]/.test(v) && /[a-z]/.test(v)) + (/\d|[^\w\s]/.test(v)));
    meter.firstChild.style.width = `${score * 25}%`; meter.dataset.s = String(score);
  });
  const form = h("form", { class: "ac-form pwform", novalidate: true, onsubmit: async (e) => {
    e.preventDefault(); msg.replaceChildren(); msg.className = "ac-msg";
    if (nw.value.length < 10) { msg.className = "ac-msg err"; msg.append("Please choose at least 10 characters."); return; }
    if (nw.value !== again.value) { msg.className = "ac-msg err"; msg.append("The two new passwords don’t match."); return; }
    go.disabled = true; go.textContent = "Saving…";
    try { await api("password", { method: "POST", body: { current: cur.value, new: nw.value } }); form.reset(); meter.firstChild.style.width = "0"; msg.className = "ac-msg ok"; msg.append(icon("info", 16), "Password changed. Other devices have been signed out."); }
    catch (ex) { msg.className = "ac-msg err"; msg.append(icon("info", 16), ex.message); }
    go.disabled = false; go.textContent = "Change password";
  } },
    h("div", { class: "ac-field" }, h("label", { for: "cur" }, "Current password"), cur),
    h("div", { class: "ac-field" }, h("label", { for: "new" }, "New password"), nw, meter, h("small", null, "At least 10 characters. A few random words is a strong choice.")),
    h("div", { class: "ac-field" }, h("label", { for: "again" }, "Repeat new password"), again), msg, go);
  return block("ac-security", "Sign-in and security", null,
    h("dl", { class: "ac-facts" }, h("dt", null, "Your ID"), h("dd", null, h("b", { class: "mono" }, p.id), " Needed, with your password, every time you sign in."),
      h("dt", null, "Automatic sign-out"), h("dd", null, "After 20 minutes without activity."), h("dt", null, "Password"), h("dd", null, p.guest ? "Guest mode has none." : "Stored only as a salted hash, never as the password itself.")),
    p.guest ? null : h("details", { class: "ac-fold" }, h("summary", null, "Change your password"), form),
    p.guest ? null : recoveryFold(p), p.guest ? null : deleteFold());
}

// ------------------------------------------------------------------ 3. your data
function dataBlock(p) {
  const msg = h("span", { class: "fine", role: "status", "aria-live": "polite" });
  const dl = h("button", { class: "btn", type: "button", disabled: p.guest || null, onclick: async () => {
    msg.textContent = "Preparing your file…";
    try {
      const data = await api("export", { fresh: true });
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const a = h("a", { href: url, download: `pranasync-${p.id}-${new Date().toISOString().slice(0, 10)}.json` }); document.body.append(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      msg.textContent = "Downloaded.";
    } catch (ex) { msg.textContent = ex.message; }
  } }, "Download a copy of my data");
  const docs = h("span", { class: "faint" }, p.guest ? "Not available in guest mode" : "Counting…");
  if (!p.guest) api("documents", { fresh: true }).then((d) => { docs.textContent = `${d.documents.length} document${d.documents.length === 1 ? "" : "s"} uploaded`; }).catch(() => { docs.textContent = ""; });
  return block("ac-data", "Your data", "Add to it, check it, or take a copy.",
    h("div", { class: "ac-cards" },
      h("div", { class: "ac-card" }, h("h3", null, "Documents"), docs, h("p", null, "Lab reports, visit notes, tracker exports. Delete one and the values read from it go with it."), h("a", { class: "btn solid", href: "#/upload" }, "Upload or manage documents")),
      h("div", { class: "ac-card" }, h("h3", null, "A copy of your data"), h("p", null, "Your details, your documents list, every value read from them and your risk classes, as one file."), dl, msg),
      p.mode === "uploads" ? null : h("div", { class: "ac-card" }, h("h3", null, "Data quality"), h("p", null, "How complete and clean your record is: missing days, duplicate rows, unit conversions."), h("a", { class: "btn", href: "#/clinical/quality" }, "Open the data quality report")),
      p.admin ? h("div", { class: "ac-card" }, h("h3", null, "Administration"), h("p", null, "Read-only access to the document store. Every document you open is written to the audit log."), h("a", { class: "btn", href: "#/admin" }, "Open the administrator document viewer")) : null,
      h("div", { class: "ac-card" }, h("h3", null, "Paper copy"), h("p", null, "Print this page, or save it as a PDF to bring to an appointment."), h("button", { class: "btn", type: "button", onclick: () => window.print() }, "Print or save as PDF"))));
}

// ------------------------------------------------------------------ 4. what we keep
function privacyBlock() {
  return block("ac-privacy", "What we keep, and who sees it", null,
    h("ul", { class: "list-x" }, ["Only you, signed in with your ID, see your record. People cannot see each other’s.", "We store a salted hash of your password, never the password itself.",
      "Documents you upload are kept for your account on this server. We store the values we read from them, with the line each came from.",
      "Your health values go to the AI models only as computed facts, and the medical-insights model runs on this computer.",
      "Every sign-in and every edit is written to a security log (which field changed, never the value)."].map((t) => h("li", null, t))));
}

export function accountView(p, { onChanged } = {}) {
  const state = {};
  const root = h("div", { class: "page account" }, pagehead("Account", p.guest ? "You are looking at a sample record in guest mode." : "Your details, your security and your data, in one place."), summary(p, state));
  const side = h("nav", { class: "ac-nav", "aria-label": "On this page" }, h("b", null, "On this page"),
    SECTIONS.map(([id, label]) => h("a", { href: "#/account", "data-id": id, onclick: jump(id) }, label)));
  const main = h("div", { class: "ac-main" }, detailsBlock(p, state, onChanged), securityBlock(p), dataBlock(p), privacyBlock());
  root.append(h("div", { class: "ac-layout" }, side, main));
  if ("IntersectionObserver" in window) {      // keep the side list in step with what is on screen
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) side.querySelectorAll("a").forEach((a) => (a.dataset.id === e.target.id ? a.setAttribute("aria-current", "true") : a.removeAttribute("aria-current"))); }), { rootMargin: "-20% 0px -65% 0px" });
    queueMicrotask(() => main.querySelectorAll(".ac-block").forEach((s) => io.observe(s)));
  }
  return root;
}
