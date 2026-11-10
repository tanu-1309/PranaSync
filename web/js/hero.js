// The top of the Home page: a short, plain headline, one ring that shows how many measures are in their usual range, and two clear next steps.
// Also a thin reading-progress bar for the whole portal.
import { h, s, fmtDate, icon } from "./ui.js";
import { mountBg } from "./bg.js";

const calm = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

function ring(done, total) {
  const R = 54, C = 2 * Math.PI * R, frac = total ? done / total : 0;
  const arc = s("circle", { cx: 70, cy: 70, r: R, class: "arc", "stroke-dasharray": C, "stroke-dashoffset": calm() ? C * (1 - frac) : C, transform: "rotate(-90 70 70)" });
  if (!calm()) requestAnimationFrame(() => requestAnimationFrame(() => { arc.style.strokeDashoffset = String(C * (1 - frac)); }));
  return s("svg", { viewBox: "0 0 140 140", class: "ring", role: "img", "aria-label": `${done} of ${total} measures within their usual range` },
    s("circle", { cx: 70, cy: 70, r: R, class: "track" }), arc,
    s("text", { x: 70, y: 74, class: "rn", "text-anchor": "middle" }, String(done)), s("text", { x: 70, y: 94, class: "rs", "text-anchor": "middle" }, `of ${total}`));
}

export function hero(p, hl) {
  const R = p.reference?.items || [];
  const within = R.filter((i) => i.flag === "within").length;
  const first = String(hl.text).split(/(?<=\.)\s/)[0];
  const ask = (q) => document.dispatchEvent(new CustomEvent("prana:ask", { detail: q }));
  const seeLevels = (e) => { e.preventDefault(); const d = document.getElementById("levels"); d?.setAttribute("open", ""); d?.scrollIntoView({ behavior: "smooth" }); };
  const el = h("section", { class: "home-hero" },
    h("div", { class: "hh-copy" },
      h("span", { class: "pill" }, `Your health record · ${fmtDate(p.window[0], "month")} to ${fmtDate(p.window[1], "month")}`),
      h("h1", null, hl.title),
      h("p", { class: "lede" }, first),
      h("div", { class: "hh-cta" },
        h("button", { class: "cta solid", type: "button", onclick: () => ask("Give me a summary") }, "Chat with Prana"),
        h("a", { class: "cta", href: "#/outlook" }, "See where it’s heading")),
      h("p", { class: "tiny" }, icon("shield", 15), "Describes your own data. Not a diagnosis.")),
    R.length ? h("div", { class: "hh-card" }, ring(within, R.length),
      h("div", null, h("b", null, "measures in their usual range"), h("span", null, "Compared with published guidelines"), h("a", { href: "#/", onclick: seeLevels }, "See which ones →"))) : null);
  mountBg(el, { rgb: "109,47,166", density: 11000 });
  return el;
}

export function pageFx() {
  const bar = h("div", { class: "progress", "aria-hidden": "true" });
  document.body.append(bar);
  let tick = false;
  addEventListener("scroll", () => {
    if (tick) return;
    tick = true;
    requestAnimationFrame(() => {
      const max = document.documentElement.scrollHeight - innerHeight;
      bar.style.transform = `scaleX(${max > 0 ? scrollY / max : 0})`;
      tick = false;
    });
  }, { passive: true });
}
