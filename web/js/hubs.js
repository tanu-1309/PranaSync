// The three pages that hold several related views as tabs: Trends & labs, Analytics & outlook, How it works.
// Each tab is its own address (#/records/labs), so the back button, bookmarks and shared links all work, and a screen reader hears one page title and a list of tabs.
import { h } from "./ui.js";
import { timelineView, labsView, medsView, historyView, helpView, pagehead } from "./record.js";
import { outlookView } from "./outlook.js";
import { analyticsView } from "./analytics.js";
import { outlookRisk } from "./risk.js";
import { helpAsync } from "./homeparts.js";
import { methodView, evidenceView } from "./method.js";
import { modelsView } from "./models.js";
import { architectureView } from "./architecture.js";

function tabs(base, items, current, aria) {
  return h("nav", { class: "tabs", "aria-label": aria }, items.map(([k, label, count]) =>
    h("a", { href: `#/${base}/${k}`, class: "tab", "aria-current": k === current ? "page" : null }, label, count ? h("span", { class: "cnt", "aria-label": `${count} items` }, count) : null)));
}

// The old pages each had their own big heading. Inside a tab the page has one, so turn the old heading into a short lead-in line.
function inner(view) {
  const ph = view.querySelector(":scope > .pagehead");
  if (ph) {
    const p = ph.querySelector("p");
    if (p) { p.className = "tab-lead"; ph.replaceWith(p); } else ph.remove();
  }
  view.classList.remove("page");
  view.classList.add("tab-body");
  return view;
}

export async function hub({ title, lead, base, items, sub, render, side, aria }) {
  const key = items.some(([k]) => k === sub) ? sub : items[0][0];
  const body = h("div", { class: "tab-panel", role: "region", "aria-label": items.find(([k]) => k === key)[1] });
  body.append(inner(await render(key)));
  return h("div", { class: "page hub" },
    h("div", { class: "hub-head" }, pagehead(title, lead), side || null),
    tabs(base, items, key, aria), body);
}

// Trends & labs ------------------------------------------------------------------------------------------
export const RECORD_TABS = [["trends", "Trends"], ["labs", "Labs"], ["medicines", "Medicines"], ["history", "History and notes"]];
export function recordsView(me, sub) {
  const views = { trends: timelineView, labs: labsView, medicines: medsView, history: historyView };
  return hub({ title: "Trends and labs", lead: "How your measurements have moved, your lab results, your medicines and your history, in one place.", base: "records", items: RECORD_TABS, sub,
    render: (k) => views[k](me), aria: "Trends and labs sections" });
}

export const INSIGHT_LABELS = { outlook: "Outlook", analytics: "Analytics and intelligence", help: "What would help" };
// Analytics & outlook ------------------------------------------------------------------------------------
export function insightsView(me, sub, asks) {
  const upload = me.mode === "uploads";
  const items = upload ? [["outlook", "Outlook"]] : [["outlook", "Outlook"], ["analytics", "Analytics and intelligence"], ["help", "What would help", asks || null]];
  const side = h("aside", { class: "hub-side", "aria-label": "Clinical view" },
    h("a", { class: "btn solid", href: "#/clinical" }, "Open the clinical view"),
    h("small", null, "For a doctor: statistical findings, every lab value, the risk model’s workings and the documents behind it."));
  const render = (k) => {
    if (upload) return h("div", null, outlookRisk(), helpAsync(me));
    return { outlook: outlookView, analytics: analyticsView, help: helpView }[k](me);
  };
  return hub({ title: "Analytics and outlook", lead: upload ? "Your three health areas, with the reasons and what is missing." : "Where things are heading, what the data and the medical model make of it, and what would help.",
    base: "insights", items, sub, render, side, aria: "Analytics and outlook sections" });
}

// How it works -------------------------------------------------------------------------------------------
export const HOW_TABS = [["models", "The models"], ["architecture", "Architecture"], ["method", "How patterns are found"], ["evidence", "Evidence and limits"]];
export function howView(me, sub) {
  const views = { models: () => modelsView(me), architecture: () => architectureView(), method: () => methodView(), evidence: () => evidenceView() };
  return hub({ title: "How it works", lead: "What each part of PranaSync does, why it is there, which AI models are used, and how well each one has been checked.", base: "how", items: HOW_TABS, sub,
    render: (k) => views[k](), aria: "How it works sections" });
}
