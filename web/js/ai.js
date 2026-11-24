// The AI-written text. It is fetched once after sign-in (the server stores it per patient, so later visits are instant) and every view reads it from `p.ai`.
// Statuses: "loading" (the model is writing), "ready", or "unavailable" (the model is off, busy, out of quota, or its text failed a safety check).
// There is no template text to fall back on: when the AI is unavailable the page says so and the statistical findings still work.
import { h, api } from "./ui.js";

export function startAI(p, onChange) {
  p.ai = { status: "loading" };
  onChange();
  api("narrative", { fresh: true })
    .then((d) => { p.ai = d.available ? { status: "ready", ...d } : { status: "unavailable", reason: d.reason }; })
    .catch((e) => { p.ai = { status: "unavailable", reason: e.status === 429 ? "Please wait a moment and try again." : "The AI text could not be loaded." }; })
    .finally(onChange);
}

export const aiReady = (p) => p.ai?.status === "ready";

// A banner shown while the AI is writing, or when it is unavailable (with a button to try again).
export function aiNotice(p, retry) {
  const s = p.ai?.status;
  if (s === "ready") return null;
  if (s === "unavailable") {
    return h("div", { class: "ainote bad", role: "status" }, h("span", null, h("b", null, "AI text is not available right now. "), p.ai.reason || ""), retry ? h("button", { type: "button", onclick: retry }, "Try again") : null);
  }
  return h("div", { class: "ainote loading", role: "status" }, h("i", { class: "spin" }), h("span", null, h("b", null, "The AI is reading your record "), "and writing this page. It can take up to a minute the first time."));
}

export const aiBadge = (p) => {
  if (!aiReady(p)) return null;
  const sample = /sample/i.test(p.ai.model || "");   // text stored by hand for a layout check is never labelled as AI
  return h("span", { class: "aibadge", title: sample ? "Sample text stored by hand to check the layout. It was not written by an AI model." : `Written by an AI model (${p.ai.model || "AI"}) from your record. The numbers come from your record.` }, sample ? "Sample text (not AI)" : "✦ AI-written");
};

// A line of placeholder shimmer while the AI is writing.
export const shimmer = (lines = 2) => h("div", { class: "shimmer-block", "aria-hidden": "true" }, Array.from({ length: lines }, (_, i) => h("i", { style: { width: `${92 - i * 14}%` } })));
