// Account page: change your own password. Sessions on other devices end when it changes.
import { h, api, icon } from "./ui.js";
import { pagehead } from "./record.js";

export function accountView(p, { onChanged }) {
  if (p.guest) {
    return h("div", { class: "page" }, pagehead("Account", "You are looking at a sample record in guest mode."),
      h("p", { class: "note" }, "Guest mode has no password and nothing personal. Sign in with your own ID to manage your account."));
  }
  const field = (id, label, auto) => h("input", { id, type: "password", autocomplete: auto, required: true, maxlength: "200" });
  const cur = field("cur", "Current password", "current-password"), nw = field("new", "New password", "new-password"), again = field("again", "Repeat new password", "new-password");
  const msg = h("div", { class: "err", role: "alert", "aria-live": "polite" }), go = h("button", { class: "btn solid", type: "submit" }, "Change password");
  const meter = h("div", { class: "meter" }, h("i")), hint = h("small", { class: "fine" }, "At least 10 characters. A few random words is a strong choice.");
  nw.addEventListener("input", () => {
    const v = nw.value, score = Math.min(4, (v.length >= 10) + (v.length >= 14) + (/[A-Z]/.test(v) && /[a-z]/.test(v)) + (/\d|[^\w\s]/.test(v)));
    meter.firstChild.style.width = `${score * 25}%`; meter.dataset.s = String(score);
  });
  const form = h("form", { class: "pwform", novalidate: true, onsubmit: async (e) => {
    e.preventDefault(); msg.replaceChildren(); msg.className = "err";
    if (nw.value.length < 10) { msg.append("Please choose at least 10 characters."); return; }
    if (nw.value !== again.value) { msg.append("The two new passwords don’t match."); return; }
    go.disabled = true; go.textContent = "Saving…";
    try { await api("password", { method: "POST", body: { current: cur.value, new: nw.value } }); form.reset(); meter.firstChild.style.width = "0"; msg.className = "ok"; msg.append(icon("info", 16), "Password changed. Other devices have been signed out."); onChanged?.(); }
    catch (ex) { msg.append(icon("info", 16), ex.message); }
    go.disabled = false; go.textContent = "Change password";
  } },
    h("label", { class: "field" }, h("span", null, "Current password"), cur),
    h("label", { class: "field" }, h("span", null, "New password"), nw, meter, hint),
    h("label", { class: "field" }, h("span", null, "Repeat new password"), again),
    msg, go);
  return h("div", { class: "page" }, pagehead("Account", `Signed in as ${p.id}. Change the password your care team issued to one only you know.`),
    h("div", { class: "card acct" }, h("h3", null, "Change your password"), form,
      h("p", { class: "fine" }, "We never store your password, only a salted hash. After a change, you stay signed in here and every other device is signed out.")));
}
