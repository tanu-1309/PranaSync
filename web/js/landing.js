// Public landing page, shown before sign-in. Everything on it is illustrative sample content or plain statements about the product:
// no customer logos, quotes or outcome claims. Interactive pieces: pointer-parallax hero cards, a scroll story whose picture follows the chapter,
// count-up numbers, clickable example questions, and an FAQ.
import { h, s, clear, logo, icon } from "./ui.js";
import { mountBg } from "./bg.js";

const calm = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const fine = () => matchMedia("(hover: hover) and (pointer: fine)").matches;

// ---------------------------------------------------------------- hero cards (sample data)
function spark(points, cls = "") {
  const W = 220, H = 60, lo = Math.min(...points), hi = Math.max(...points);
  const d = points.map((v, i) => `${i ? "L" : "M"}${(i / (points.length - 1) * W).toFixed(1)},${(H - 6 - ((v - lo) / (hi - lo || 1)) * (H - 12)).toFixed(1)}`).join(" ");
  return s("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none", class: `spark ${cls}`, "aria-hidden": "true" }, s("path", { d, class: "sl" }));
}

// ---------------------------------------------------------------- hero picture: floating sample cards
function heroCards() {
  const wrap = h("div", { class: "lp-visual", "aria-hidden": "true" },
    h("div", { class: "lp-blob b1" }), h("div", { class: "lp-blob b2" }),
    h("div", { class: "fl c1", "data-depth": "18" }, h("span", { class: "k" }, "Heart attack or stroke, 10 years"), h("b", null, "2 in 100"), h("span", { class: "chip ok" }, "low band")),
    h("div", { class: "fl c2", "data-depth": "30" }, h("span", { class: "k" }, "Blood pressure"), spark([138, 137, 139, 138, 140, 139, 141, 141]), h("span", { class: "chip warn" }, "↗ rising steadily")),
    h("div", { class: "fl c3", "data-depth": "12" }, s("svg", { viewBox: "0 0 70 70", class: "mini" }, s("circle", { cx: 35, cy: 35, r: 28, class: "t" }), s("circle", { cx: 35, cy: 35, r: 28, class: "a", "stroke-dasharray": "176", "stroke-dashoffset": "70", transform: "rotate(-90 35 35)" })),
      h("div", null, h("b", null, "17 of 28"), h("span", { class: "k" }, "in their usual range"))),
    h("div", { class: "fl c4", "data-depth": "24" }, icon("shield", 16), "Sample data. Not a diagnosis."));
  if (fine() && !calm()) {
    const kids = [...wrap.querySelectorAll(".fl")];
    wrap.addEventListener("pointermove", (e) => {
      const r = wrap.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
      kids.forEach((k) => { const d = Number(k.dataset.depth); k.style.translate = `${x * d}px ${y * d}px`; });
    });
    wrap.addEventListener("pointerleave", () => wrap.querySelectorAll(".fl").forEach((k) => { k.style.translate = ""; }));
  }
  return wrap;
}

function heroVisual() {
  return h("div", { class: "hero-slot" }, heroCards());
}

// ---------------------------------------------------------------- scroll story
const CHAPTERS = [
  ["01", "See what changed", "Every measurement is compared with your own first two months, not with other people. When several related signals start moving together and stay moved, we say so, in plain words."],
  ["02", "Know where you stand", "A second check asks whether each level sits within a usual range from published guidelines. You see a calm card for each measure, not a wall of numbers."],
  ["03", "Ask and prepare", "Ask Prana about your own record. Get your 10-year heart and diabetes estimates with the reasons behind them, and a short list of questions for your next visit."],
];

function visual(i) {
  if (i === 0) {
    const rows = [[3, 7, 4, 6, 5, 6, 4, 5], [5, 4, 6, 5, 5, 4, 6, 5], [4, 5, 4, 5, 6, 8, 11, 14], [6, 5, 5, 6, 5, 7, 10, 13], [5, 6, 5, 4, 5, 8, 12, 15]];
    return h("div", { class: "vis v0" }, h("p", { class: "k" }, "Five measurements, one year (sample)"),
      rows.map((r, k) => h("div", { class: `vrow${k >= 2 ? " moved" : ""}` }, spark(r))), h("span", { class: "chip warn" }, "3 signals moved together"));
  }
  if (i === 1) {
    const bars = [["Blood pressure", 64, "warn", "Above typical"], ["HbA1c", 52, "warn", "Above typical"], ["Resting heart rate", 30, "ok", "Within range"], ["Sleep", 38, "ok", "Within range"]];
    return h("div", { class: "vis v1" }, h("p", { class: "k" }, "Where you sit against usual ranges (sample)"),
      bars.map(([n, w, t, c]) => h("div", { class: "lvl" }, h("b", null, n), h("div", { class: "track" }, h("i", { class: t, style: { width: `${w}%` } })), h("span", { class: `chip ${t}` }, c))));
  }
  return h("div", { class: "vis v2" }, h("p", { class: "k" }, "Your 10-year estimates (sample)"),
    h("div", { class: "two" }, h("div", null, h("span", { class: "k" }, "Heart attack or stroke"), h("b", null, "2 in 100"), h("span", { class: "chip ok" }, "low")), h("div", null, h("span", { class: "k" }, "Type 2 diabetes"), h("b", null, "15–20 pts"), h("span", { class: "chip warn" }, "high band"))),
    h("p", { class: "why" }, "Mostly from cholesterol and blood pressure. Each factor’s share is shown, and what the estimate does not include."));
}

function story() {
  const panels = CHAPTERS.map((_, i) => h("div", { class: `panel${i === 0 ? " on" : ""}` }, visual(i)));
  const items = CHAPTERS.map(([n, t, d], i) => h("article", { class: `chap${i === 0 ? " on" : ""}`, "data-i": i }, h("span", { class: "n" }, n), h("h3", null, t), h("p", null, d)));
  const el = h("section", { class: "lp-story", id: "how" },
    h("h2", null, "From a year of numbers to a clear picture"),
    h("div", { class: "grid" }, h("div", { class: "chaps" }, items), h("div", { class: "stage" }, h("div", { class: "stage-in" }, panels))));
  const io = new IntersectionObserver((es) => es.forEach((e) => {
    if (!e.isIntersecting) return;
    const i = Number(e.target.dataset.i);
    items.forEach((x, k) => x.classList.toggle("on", k === i)); panels.forEach((x, k) => x.classList.toggle("on", k === i));
  }), { rootMargin: "-45% 0px -45% 0px" });
  items.forEach((x) => io.observe(x));
  items.forEach((x, i) => x.addEventListener("pointerenter", () => { items.forEach((y, k) => y.classList.toggle("on", k === i)); panels.forEach((y, k) => y.classList.toggle("on", k === i)); }));
  return el;
}

// ---------------------------------------------------------------- Meet Prana (canned examples, labelled as such)
const QA = [
  ["What is my chance of a heart attack?", "About 2 in 100 over the next 10 years, which is the low band. It comes mostly from total cholesterol and blood pressure. I can show each factor’s share and what the estimate leaves out."],
  ["Did anything change for me?", "Three related measures began moving together in February: HbA1c, fasting glucose and triglycerides. This links to a note already in your history. I can show you which ones, and what to ask your doctor."],
  ["Should I stop my medicine?", "I can’t advise on medicines or doses. Please ask your pharmacist or the clinician who prescribed it. I can show what is on your record and how consistently doses were taken."],
];

function meet() {
  const log = h("div", { class: "qa-log", "aria-live": "polite" });
  const say = (i) => {
    log.append(h("div", { class: "b me" }, QA[i][0]));
    const t = h("div", { class: "b bot typing" }, h("i"), h("i"), h("i")); log.append(t);
    setTimeout(() => { t.replaceWith(h("div", { class: "b bot" }, QA[i][1])); log.scrollTop = log.scrollHeight; }, calm() ? 0 : 900);
    log.scrollTop = log.scrollHeight;
  };
  return h("section", { class: "lp-meet", id: "prana" },
    h("div", { class: "copy" }, h("span", { class: "eyebrow" }, "Hi, I’m Prana"),
      h("h2", null, "Questions about your record, answered in plain words"),
      h("p", null, "Prana answers only from your own data. It will tell you what it can’t do, and it never diagnoses."),
      h("div", { class: "qs" }, QA.map((q, i) => h("button", { type: "button", onclick: () => say(i) }, q[0]))),
      h("p", { class: "fine" }, "These are example answers from a sample record. Sign in, or try the sample, to ask your own.")),
    h("div", { class: "qa" }, h("div", { class: "qa-head" }, h("span", { class: "av" }, "P"), h("div", null, h("b", null, "Prana"), h("small", null, "Online · answers from your record only"))), log));
}

// ---------------------------------------------------------------- numbers, privacy, FAQ
function numbers() {
  const items = [[28, "measures compared with published guidelines"], [2, "10-year risk scores: heart and diabetes"], [0, "diagnoses made, ever"], [900, "practice records used to build and test it"]];
  const el = h("section", { class: "lp-nums" }, items.map(([n, l]) => h("div", null, h("b", { "data-n": n }, "0"), h("span", null, l))));
  new IntersectionObserver((es, o) => es.forEach((e) => {
    if (!e.isIntersecting) return;
    o.disconnect();
    el.querySelectorAll("[data-n]").forEach((b) => {
      const to = Number(b.dataset.n), t0 = performance.now();
      const step = (t) => { const k = Math.min(1, (t - t0) / 1100); b.textContent = Math.round(to * (1 - (1 - k) ** 3)).toLocaleString(); if (k < 1 && !calm()) requestAnimationFrame(step); else b.textContent = to.toLocaleString(); };
      requestAnimationFrame(step);
    });
  }), { threshold: 0.4 }).observe(el);
  return el;
}

const TRUST = [["shield", "Only you see your record", "Each person has their own ID and password. The server decides who you are from your sign-in, never from what you type."],
  ["info", "Describes, never diagnoses", "We show what changed in your own data and give you questions for your care team. A clinician makes the decisions."],
  ["question", "Says what it can’t do", "Prana will not advise on medicines, assess emergencies, or estimate conditions it has no validated score for."]];
const FAQ = [["Is this a medical device or a diagnosis?", "No. PranaSync is a prototype that describes patterns in your own data. It is not medical advice and does not diagnose."],
  ["Where does the heart-risk number come from?", "From the published ACC/AHA Pooled Cohort Equations. The diabetes score is the Finnish Diabetes Risk Score. Smoking and waist size are not in the records, so the answers say what is assumed."],
  ["Can I use it without an account?", "Yes. “Try the sample record” opens a read-only example so you can look around. Nothing you do there changes anything."],
  ["Who built this?", "Team 8 for the PranaChain × University of Windsor “Beyond the Record” challenge (COMP 8967). It is a student prototype, tested on practice data, not yet clinically validated."]];

function trust() {
  return h("section", { class: "lp-trust", id: "privacy" }, h("h2", null, "Built to be trusted"),
    h("div", { class: "cards" }, TRUST.map(([ic, t, d]) => h("article", null, h("span", { class: "ic" }, icon(ic, 22)), h("h3", null, t), h("p", null, d)))));
}

function faq() {
  return h("section", { class: "lp-faq", id: "faq" }, h("h2", null, "Good questions"), FAQ.map(([q, a]) => h("details", null, h("summary", null, q), h("p", null, a))));
}

// ---------------------------------------------------------------- page
export function landingView(root, { onSignIn, onGuest }) {
  const nav = h("header", { class: "lp-nav" }, h("a", { class: "wm", href: "#", onclick: (e) => { e.preventDefault(); scrollTo({ top: 0, behavior: "smooth" }); } }, logo(34), h("b", null, "PranaSync")),
    h("nav", { "aria-label": "Page sections" }, [["how", "How it works"], ["prana", "Meet Prana"], ["privacy", "Privacy"], ["faq", "FAQ"]].map(([id, l]) =>
      h("a", { href: `#${id}`, onclick: (e) => { e.preventDefault(); document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }); } }, l))),
    h("div", { class: "r" }, h("button", { class: "lp-btn ghost", type: "button", onclick: onSignIn }, "Sign in"), h("button", { class: "lp-btn solid", type: "button", onclick: onGuest }, "Try the sample")));
  addEventListener("scroll", () => nav.classList.toggle("scrolled", scrollY > 8), { passive: true });

  const hero = h("section", { class: "lp-hero" },
    h("div", { class: "copy" }, h("span", { class: "eyebrow" }, "Patient health record"),
      h("h1", null, "Your health record, ", h("em", null, "made clear.")),
      h("p", { class: "lede" }, "A year of your readings, compared with your own usual, explained in plain words. See what changed, where you stand, and what to ask your doctor. Never a diagnosis."),
      h("div", { class: "lp-row" }, h("button", { class: "lp-btn solid lg", type: "button", onclick: onGuest }, "Try the sample record"), h("button", { class: "lp-btn ghost lg", type: "button", onclick: onSignIn }, "Sign in")),
      h("p", { class: "tiny" }, icon("shield", 15), "Your record opens only with your own ID and password.")),
    heroVisual());

  const cta = h("section", { class: "lp-cta" }, h("h2", null, "See your year, clearly."), h("p", null, "Sign in to your record, or look around a sample first."),
    h("div", { class: "lp-row" }, h("button", { class: "lp-btn light lg", type: "button", onclick: onGuest }, "Try the sample record"), h("button", { class: "lp-btn outline lg", type: "button", onclick: onSignIn }, "Sign in")));
  const foot = h("footer", { class: "lp-foot" }, h("span", null, "PranaSync · a student prototype for the PranaChain × University of Windsor challenge (COMP 8967)."), h("span", null, "Not a medical device. Not medical advice. Tested on practice data."));

  clear(root);
  root.append(h("div", { class: "lp" }, nav, hero, numbers(), story(), meet(), trust(), faq(), cta, foot));
  mountBg(hero, { rgb: "109,47,166" });
  mountBg(cta, { rgb: "207,154,232", density: 7000 });
  document.title = "PranaSync · Your health record, made clear";
  scrollTo(0, 0);
}
