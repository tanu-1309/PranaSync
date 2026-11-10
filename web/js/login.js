import { h, s, clear, api, logo, icon } from "./ui.js";
import { mountBg } from "./bg.js";

// Soft, abstract "signals" for the brand panel: a few smooth waves, no data.
function waves() {
  const svg = s("svg", { class: "waves", viewBox: "0 0 600 400", preserveAspectRatio: "xMidYMax slice", "aria-hidden": "true" });
  [[300, 38, 0.011, "#6d2fa6", 0.18], [330, 30, 0.015, "#9b4fc4", 0.16], [360, 24, 0.02, "#f0a17f", 0.3]].forEach(([y0, amp, f, c, o], i) => {
    let d = `M0 400 L0 ${y0}`;
    for (let x = 0; x <= 600; x += 10) d += ` L${x} ${(y0 + Math.sin(x * f + i * 2) * amp).toFixed(1)}`;
    svg.append(s("path", { d: d + " L600 400 Z", fill: c, opacity: o }));
  });
  return svg;
}

const BENEFITS = [
  ["shield", "Only you see it", "Your record opens with your own ID and password."],
  ["wave", "See what changed", "Your numbers, compared with your own usual, in plain words."],
  ["question", "Questions answered", "Ask Prana about your record once you’re in."],
];

export function loginView(root, { notice, onSuccess, onBack }) {
  const id = h("input", { id: "pid", name: "id", autocomplete: "username", autocapitalize: "characters", spellcheck: "false", required: true, placeholder: "PC0000", "aria-describedby": "err" });
  const pw = h("input", { id: "pwd", name: "password", type: "password", autocomplete: "current-password", required: true, placeholder: "Your password", "aria-describedby": "err" });
  const eye = h("button", { type: "button", "aria-label": "Show password", onclick: () => { const on = pw.type === "password"; pw.type = on ? "text" : "password"; eye.textContent = on ? "hide" : "show"; } }, "show");
  const err = h("div", { class: "err", id: "err", role: "alert" });
  const go = h("button", { class: "btn solid", type: "submit" }, "Sign in");

  const guestBtn = h("button", { class: "btn ghost", type: "button", onclick: async () => {
    guestBtn.disabled = true; guestBtn.textContent = "Opening the sample…";
    try { await api("guest", { method: "POST" }); onSuccess(); }
    catch (ex) { clear(err); err.append(icon("info", 16), ex.message); guestBtn.disabled = false; guestBtn.textContent = "Look around with a sample record"; }
  } }, "Look around with a sample record");

  const form = h("form", { novalidate: true, onsubmit: async (e) => {
    e.preventDefault();
    clear(err);
    if (!id.value.trim() || !pw.value) { err.append("Enter your ID and password."); return; }
    go.disabled = true; go.textContent = "Signing in…";
    try {
      await api("login", { method: "POST", body: { id: id.value, password: pw.value } });
      pw.value = "";
      onSuccess();
    } catch (ex) {
      err.append(icon("info", 16), ex.message);
      go.disabled = false; go.textContent = "Sign in"; pw.select();
    }
  } },
    onBack ? h("button", { class: "back", type: "button", onclick: onBack }, "← Back to home") : null,
    h("h2", null, "Welcome back"),
    h("p", { class: "sub" }, "Sign in to see your health record."),
    notice ? h("div", { class: "note banner" }, notice) : null,
    h("label", { class: "field" }, h("span", null, "Patient ID"), id),
    h("label", { class: "field" }, h("span", null, "Password"), h("div", { class: "pw" }, pw, eye)),
    err, go,
    h("div", { class: "or" }, h("span", null, "or")),
    guestBtn,
    h("p", { class: "small" }, "Use the ID and password your care team issued. You can change the password after you sign in. If you’ve lost it, ask the team to reset it."));

  clear(root);
  root.append(h("div", { class: "login" },
    h("section", { class: "side" },
      waves(),
      h("div", { class: "wm" }, logo(44), h("b", null, "PranaSync")),
      h("div", { class: "pitch" },
        h("h1", null, "Your health record,", h("br"), h("em", null, "made clear.")),
        h("p", { class: "cap" }, "A year of your readings, explained simply. Never a diagnosis."),
        h("ul", { class: "benefits" }, BENEFITS.map(([ic, t, d]) => h("li", null, h("span", { class: "bi" }, icon(ic, 20)), h("div", null, h("b", null, t), h("span", null, d))))))),
    h("section", { class: "main", id: "main" }, form)));
  mountBg(root.querySelector(".side"), { rgb: "109,47,166" });
  id.focus();
}
