// "Prana": the assistant. A friendly panel that answers questions about the signed-in patient's own record.
// The server decides who the patient is; answers are built from that record only.
import { h, clear, md, api } from "./ui.js";

const STARTERS = [
  ["How am I doing?", "Give me a summary"],
  ["My health risks", "What are my health risks?"],
  ["What changed for me?", "Did anything change for me?"],
  ["What to ask my doctor", "What should I ask my doctor?"],
];

export function mountChat(host) {
  let state = {}, busy = false, started = false;
  const log = h("div", { class: "chat-log", role: "log", "aria-live": "polite" });
  const sugg = h("div", { class: "chat-sugg" });
  const input = h("input", { type: "text", maxlength: "500", placeholder: "Ask about your record…", "aria-label": "Your question", autocomplete: "off" });
  const send = h("button", { class: "sendbtn", type: "submit", "aria-label": "Send" }, "➤");
  const panel = h("section", { class: "chat-panel", id: "chat-panel", hidden: true, "aria-label": "Ask Prana about your record" },
    h("header", null, h("span", { class: "av" }, "P"), h("div", null, h("b", null, "Prana"), h("small", null, h("i"), "Online · answers from your record only")),
      h("button", { class: "x", "aria-label": "Close", onclick: () => toggle(false) }, "×")),
    log, sugg,
    h("form", { onsubmit: (e) => { e.preventDefault(); ask(input.value); } }, input, send),
    h("p", { class: "fine" }, "Prana describes your data. It can’t diagnose, advise on medicines or help in an emergency."));
  const fab = h("button", { class: "chat-fab", "aria-expanded": "false", "aria-controls": "chat-panel", onclick: () => toggle(panel.hidden) }, h("span", { class: "av" }, "P"), "Ask Prana");
  host.append(fab, panel);
  document.addEventListener("prana:ask", (e) => { if (panel.hidden) toggle(true); ask(e.detail); });

  function toggle(open) {
    panel.hidden = !open; fab.setAttribute("aria-expanded", String(open));
    if (open) { if (!started) welcome(); input.focus(); }
  }
  function welcome() {
    started = true;
    bubble("bot", [h("p", null, "Hi, I’m ", h("b", null, "Prana"), ". Ask me about your own record, in your own words, or pick a place to start.")]);
    chips(STARTERS);
  }
  function chips(list) {
    clear(sugg);
    list.forEach((t) => { const [label, q] = Array.isArray(t) ? t : [t, t]; sugg.append(h("button", { type: "button", onclick: () => ask(q, label) }, label)); });
  }
  function bubble(who, nodes) { const b = h("div", { class: `msg ${who}` }, nodes); log.append(b); log.scrollTop = log.scrollHeight; return b; }
  function links(sources) {
    return sources && sources.length ? h("p", { class: "msg-src" }, "See: ", sources.map((x, i) => [i ? " · " : "", h("a", { href: x.link }, x.label)])) : null;
  }
  function render(r) {
    bubble("bot", [r.answer.flatMap((t) => md(t)), links(r.sources)]);
    chips(r.suggestions);
  }
  async function ask(text, label) {
    text = text.trim();
    if (busy || !text) return;
    bubble("me", label || text);
    input.value = ""; busy = true; send.disabled = true; clear(sugg);
    const typing = bubble("bot typing", [h("i"), h("i"), h("i")]);
    try { await new Promise((r) => setTimeout(r, 450)); const r = await api("chat", { method: "POST", body: { message: text, state } }); state = r.state; typing.remove(); render(r); }
    catch (e) { typing.remove(); bubble("bot", e.status === 401 ? "You were signed out. Please sign in again." : (e.message || "Sorry, I couldn’t answer that.")); }
    busy = false; send.disabled = false; input.focus();
  }
}
