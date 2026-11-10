// Small interactions: content eases in as it scrolls into view, headline numbers count up, cards respond to the pointer.
// All of it is skipped for people who ask their system for reduced motion.
const calm = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const REVEAL = ".card, .rec, .recgroup, .finding, .lab, .panel, .askrow, .outlook-sec > h2, .standfirst, .note, .med, .tl-row";

let io;
export function enhance(root) {
  if (calm() || !("IntersectionObserver" in window)) return;
  io ??= new IntersectionObserver((entries) => entries.forEach((e) => {
    if (!e.isIntersecting) return;
    e.target.classList.add("in"); io.unobserve(e.target);
    e.target.querySelectorAll("[data-count]").forEach(countUp);
  }), { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
  root.querySelectorAll(REVEAL).forEach((el, i) => {
    el.classList.add("reveal"); el.style.setProperty("--d", `${Math.min(i % 6, 5) * 60}ms`); io.observe(el);
  });
  // safety net: if the observer never fires (hidden tab, odd browser), nothing stays invisible
  setTimeout(() => root.querySelectorAll(".reveal:not(.in)").forEach((el) => { el.classList.add("in"); el.querySelectorAll("[data-count]").forEach(countUp); }), 1500);
}

export function countUp(el) {
  const to = parseFloat(el.dataset.count), nd = Number(el.dataset.nd || 0);
  if (Number.isNaN(to) || calm()) { el.textContent = to.toFixed(nd); return; }
  const t0 = performance.now(), dur = 900;
  const step = (t) => {
    const k = Math.min(1, (t - t0) / dur), eased = 1 - Math.pow(1 - k, 3);
    el.textContent = (to * eased).toFixed(nd);
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// Cards tilt their highlight toward the pointer (sets --mx / --my, used by the CSS glow).
export function glow(root) {
  root.addEventListener("pointermove", (e) => {
    const c = e.target.closest?.(".card, .rec, .finding");
    if (!c) return;
    const r = c.getBoundingClientRect();
    c.style.setProperty("--mx", `${e.clientX - r.left}px`); c.style.setProperty("--my", `${e.clientY - r.top}px`);
  }, { passive: true });
}
