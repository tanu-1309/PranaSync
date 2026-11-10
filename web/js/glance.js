// "At a glance": the few things a patient most wants to know, before any detail. Each card leads to the fuller page.
import { h, icon } from "./ui.js";

function card({ href, tone, kicker, big, small, foot, onclick, ic }) {
  const el = h(href ? "a" : "button", { class: `gl tone-${tone}`, href, type: href ? null : "button", onclick },
    h("span", { class: "gic" }, icon(ic || "info", 22)), h("span", { class: "gk" }, kicker), h("b", { class: "gb" }, big), h("span", { class: "gs" }, small), h("span", { class: "gf" }, foot, " →"));
  return el;
}

export function glance(p, hl) {
  const patterns = p.scenarios.filter((s) => s.surfaced);
  const risk = p.outlook?.risk, fc = p.outlook?.forecast, rec = p.outlook?.recommendations;
  const top = rec?.groups?.[0]?.items?.[0];
  const cards = [
    card({ ic: "check", href: "#/", tone: patterns.length ? "ember" : "teal", kicker: "How you’re doing",
      big: patterns.length ? "One thing to raise" : "Nothing unusual", small: patterns.length
        ? `${patterns.length === 1 ? "An area" : patterns.length + " areas"} show${patterns.length === 1 ? "s" : ""} several signals moving together.` : "Your measurements sit close to your own usual.",
      foot: "See the finding", onclick: (e) => { e.preventDefault(); document.getElementById("found")?.setAttribute("open", ""); document.getElementById("found")?.scrollIntoView({ behavior: "smooth" }); } }),
    risk?.available
      ? card({ ic: "heart", href: "#/outlook", tone: risk.band === "low" ? "teal" : risk.band === "borderline" ? "gold" : "ember", kicker: "Heart health (10-year estimate)",
        big: `${risk.per100} in 100`, small: `${risk.band[0].toUpperCase() + risk.band.slice(1)} band. See what feeds this number.`, foot: "See the factors" })
      : card({ ic: "heart", href: "#/outlook", tone: "slate", kicker: "Heart health", big: "Not scored", small: risk?.reason?.replace(/ so no percentage is given\.?/, ".") || "Not enough information.", foot: "See what we can show" }),
    p.outlook?.diabetes?.available ? card({ ic: "drop", href: "#/outlook", tone: ["low"].includes(p.outlook.diabetes.band_max) ? "teal" : p.outlook.diabetes.band_max === "very high" || p.outlook.diabetes.band_max === "high" ? "ember" : "gold", kicker: "Diabetes risk (10-year estimate)",
      big: p.outlook.diabetes.per100_min === p.outlook.diabetes.per100_max ? `${p.outlook.diabetes.per100_min} in 100` : `${p.outlook.diabetes.per100_min}–${p.outlook.diabetes.per100_max} in 100`,
      small: `${p.outlook.diabetes.band_min === p.outlook.diabetes.band_max ? p.outlook.diabetes.band_min : p.outlook.diabetes.band_min + " to " + p.outlook.diabetes.band_max} band. See what feeds this number.`, foot: "See the factors" }) : null,
    card({ ic: "wave", href: "#/outlook", tone: fc?.items?.length ? "gold" : "teal", kicker: "Where it’s heading",
      big: fc?.items?.length ? `${fc.items.length} trend${fc.items.length > 1 ? "s" : ""} to watch` : "Holding steady",
      small: fc?.items?.length ? "A strong, lasting trend is projected 3 months ahead." : "No strong trend, so no change is predicted.", foot: "See the outlook" }),
    card({ ic: "question", tone: "violet", kicker: "Your next step", big: top ? (rec.groups[0].id === "raise" ? "Worth raising" : "Worth watching") : "Keep tracking", small: top ? top.title : "Nothing needs raising right now.",
      foot: "Ask Prana about it", onclick: () => document.querySelector(".chat-fab")?.click() }),
  ];
  return h("section", { class: "glance", "aria-label": "At a glance" }, h("h2", null, "Your health at a glance"), h("div", { class: "glgrid" }, cards.filter(Boolean)));
}
