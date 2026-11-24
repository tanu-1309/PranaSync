// Create an account: no records exist yet, the person builds one by uploading documents.
import { h, clear, api, logo, icon } from "./ui.js";
import { codesPanel } from "./codes.js";

export function registerView(root, { onSuccess, onBack, onSignIn }) {
  const name = h("input", { id: "rg-name", name: "name", autocomplete: "name", maxlength: "80", placeholder: "Optional" });
  const pw = h("input", { id: "rg-pw", name: "password", type: "password", autocomplete: "new-password", required: true, maxlength: "200", placeholder: "At least 10 characters" });
  const again = h("input", { id: "rg-pw2", type: "password", autocomplete: "new-password", required: true, maxlength: "200" });
  const err = h("div", { class: "err", role: "alert" });
  const go = h("button", { class: "btn solid", type: "submit" }, "Create my account");
  const form = h("form", { novalidate: true, onsubmit: async (e) => {
    e.preventDefault(); clear(err);
    if (pw.value.length < 10) { err.append("Please choose at least 10 characters."); return; }
    if (pw.value !== again.value) { err.append("The two passwords don’t match."); return; }
    go.disabled = true; go.textContent = "Creating…";
    try {
      const r = await api("register", { method: "POST", body: { name: name.value, password: pw.value } }); pw.value = again.value = "";
      const main = root.querySelector("#main"); clear(main); main.append(codesPanel(r.id, r.recovery_codes || [], { onDone: onSuccess }));      // the codes are shown once, before the person goes on
    }
    catch (ex) { err.append(icon("info", 16), ex.message); go.disabled = false; go.textContent = "Create my account"; }
  } },
    onBack ? h("button", { class: "back", type: "button", onclick: onBack }, "← Back to home") : null,
    h("h2", null, "Create your account"),
    h("p", { class: "sub" }, "You start with an empty record and add your own documents, one at a time."),
    h("label", { class: "field" }, h("span", null, "Name (optional)"), name),
    h("label", { class: "field" }, h("span", null, "Password"), pw),
    h("label", { class: "field" }, h("span", null, "Repeat password"), again),
    err, go,
    h("p", { class: "small" }, "We give you an ID after you sign up. Write it down: you need it, with your password, to sign in. There is no email: after you sign up you get eight one-time recovery codes. Keep them, they are the only way back in if you lose your password."),
    h("div", { class: "or" }, h("span", null, "already have an ID?")),
    h("button", { class: "btn ghost", type: "button", onclick: onSignIn }, "Sign in"));
  clear(root);
  root.append(h("div", { class: "login" },
    h("section", { class: "side" }, h("div", { class: "wm" }, logo(44), h("b", null, "PranaSync")),
      h("div", { class: "pitch" }, h("h1", null, "Start with one document.", h("br"), h("em", null, "Add more any time.")),
        h("p", { class: "cap" }, "Upload a lab report or a visit note. We read the values and show three health areas with the reasons, even from a single document."))),
    h("section", { class: "main", id: "main" }, form)));
  name.focus();
}
