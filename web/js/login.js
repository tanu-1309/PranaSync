import { h, s, clear, api, logo, icon } from "./ui.js";

// Abstract signal traces for the plum panel: deterministic sums of sines, drawn as hairlines.
function traces() {
  const W = 800, H = 900, rows = 11;
  const svg = s("svg", { class: "traces", viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "xMidYMid slice", "aria-hidden": "true" });
  for (let r = 0; r < rows; r++) {
    const y0 = 120 + r * 66, amp = 8 + ((r * 7) % 5) * 5, f1 = 0.008 + r * 0.0011, f2 = 0.021 + (r % 4) * 0.004, ph = r * 1.7;
    const shift = r === 6;
    let d = "";
    for (let x = 0; x <= W; x += 8) {
      const bump = shift && x > 470 ? Math.min(1, (x - 470) / 140) * 46 : 0;
      const y = y0 - bump + Math.sin(x * f1 + ph) * amp + Math.sin(x * f2 + ph * 2) * amp * 0.35;
      d += `${x ? "L" : "M"}${x} ${y.toFixed(1)}`;
    }
    svg.append(s("path", { d, fill: "none", "stroke-width": shift ? 1.8 : 1, style: { stroke: shift ? "#f0a17f" : "#f3efe7", opacity: shift ? 0.95 : 0.13 + (r % 3) * 0.04 } }));
  }
  svg.append(s("line", { x1: 470, x2: 470, y1: 90, y2: 850, "stroke-width": 1, style: { stroke: "#f0a17f", opacity: 0.45, strokeDasharray: "2 5" } }));
  return svg;
}

export function loginView(root, { notice, onSuccess }) {
  const id = h("input", { id: "pid", name: "id", autocomplete: "username", autocapitalize: "characters", spellcheck: "false", required: true, placeholder: "PC0000", "aria-describedby": "err" });
  const pw = h("input", { id: "pwd", name: "password", type: "password", autocomplete: "current-password", required: true, placeholder: "xxxx-xxxx-xxxx", "aria-describedby": "err" });
  const eye = h("button", { type: "button", "aria-label": "Show password", onclick: () => { const on = pw.type === "password"; pw.type = on ? "text" : "password"; eye.textContent = on ? "hide" : "show"; } }, "show");
  const err = h("div", { class: "err", id: "err", role: "alert" });
  const go = h("button", { class: "btn solid", type: "submit" }, "Sign in");

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
    h("h2", null, "Sign in"),
    h("p", { class: "sub" }, "Your record and its analysis are visible only to you."),
    notice ? h("div", { class: "note banner" }, notice) : null,
    h("label", { class: "field" }, h("span", null, "Patient ID"), id),
    h("label", { class: "field" }, h("span", null, "Password"), h("div", { class: "pw" }, pw, eye)),
    err, go,
    h("p", { class: "small" }, "Use the ID and password your care team issued. If you’ve lost them, ask the team to reset your password; there is no self-service reset."));

  clear(root);
  root.append(h("div", { class: "login" },
    h("section", { class: "side" },
      traces(),
      h("div", { class: "wm", style: { display: "flex", alignItems: "center", gap: "12px" } }, logo(34), h("div", null, h("div", { style: { font: "italic 400 24px/1 var(--serif)" } }, "PranaChain"), h("div", { class: "mono", style: { fontSize: "11px", color: "#b9a9c7", marginTop: "4px" } }, "Insight · patient portal"))),
      h("h1", null, "A year of readings, ", h("em", null, "read as a whole.")),
      h("p", { class: "cap" }, "We compare you only with your own usual, and speak up when several related signals move together. Never a diagnosis.")),
    h("section", { class: "main", id: "main" }, form)));
  id.focus();
}
