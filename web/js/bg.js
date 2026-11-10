// A moving background: heartbeat traces that scroll across, plus drifting "signals" joined by faint lines. It reacts to the pointer (nearby points are drawn toward it and linked to it)
// and a click sends a ripple outward. Pauses when off-screen or the tab is hidden; a still picture for people who ask for reduced motion.

const ecg = (p) => {   // one heartbeat, p in [0, 1)
  const g = (c, a, w) => a * Math.exp(-((p - c) ** 2) / (2 * w * w));
  return g(0.18, 0.12, 0.03) + g(0.36, -0.12, 0.008) + g(0.4, 1, 0.01) + g(0.44, -0.25, 0.01) + g(0.66, 0.25, 0.05);
};

export function mountBg(host, { rgb = "109,47,166", density = 9000, link = 130, pulses = true } = {}) {
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const cv = document.createElement("canvas");
  cv.className = "bg-canvas"; cv.setAttribute("aria-hidden", "true");
  host.prepend(cv);
  const ctx = cv.getContext("2d");
  let W = 0, H = 0, dpr = 1, nodes = [], ripples = [], raf = 0, visible = true;
  const mouse = { x: -999, y: -999, on: false };

  function size() {
    dpr = Math.min(2, devicePixelRatio || 1);
    W = host.clientWidth; H = host.clientHeight;
    cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const n = Math.max(18, Math.min(90, Math.round((W * H) / density)));
    while (nodes.length < n) nodes.push({ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - 0.5) * 0.35, vy: (Math.random() - 0.5) * 0.35, r: 1.4 + Math.random() * 1.8 });
    nodes.length = n;
    if (calm) draw();
  }

  function step() {
    for (const p of nodes) {
      if (mouse.on) {
        const dx = mouse.x - p.x, dy = mouse.y - p.y, d = Math.hypot(dx, dy);
        if (d < 170 && d > 1) { p.vx += (dx / d) * 0.012; p.vy += (dy / d) * 0.012; }
      }
      for (const r of ripples) {
        const dx = p.x - r.x, dy = p.y - r.y, d = Math.hypot(dx, dy);
        if (Math.abs(d - r.r) < 26 && d > 1) { p.vx += (dx / d) * 0.09; p.vy += (dy / d) * 0.09; }
      }
      p.vx *= 0.985; p.vy *= 0.985;
      const sp = Math.hypot(p.vx, p.vy); if (sp < 0.12) { p.vx += (Math.random() - 0.5) * 0.02; p.vy += (Math.random() - 0.5) * 0.02; }
      p.x += p.vx; p.y += p.vy;
      if (p.x < -10) p.x = W + 10; else if (p.x > W + 10) p.x = -10;
      if (p.y < -10) p.y = H + 10; else if (p.y > H + 10) p.y = -10;
    }
    ripples = ripples.filter((r) => (r.r += 5, r.r < 420));
  }

  // Heartbeat traces: they scroll left, swell when the pointer is near, and a click sends a wave along them.
  function drawTraces() {
    const t = calm ? 0 : performance.now() / 1000, rows = H > 420 ? 3 : 2;
    for (let r = 0; r < rows; r++) {
      const y0 = H * (0.3 + r * 0.27), A = Math.min(52, H * 0.075) * (1 - r * 0.14), speed = 0.42 + r * 0.1;
      ctx.beginPath();
      for (let x = 0; x <= W; x += 4) {
        let v = ecg(((x / W) * 2.6 + t * speed + r * 0.31) % 1) * A;
        if (mouse.on) v *= 1 + 1.8 * Math.exp(-((x - mouse.x) ** 2) / (2 * 90 * 90)) * Math.exp(-((y0 - mouse.y) ** 2) / (2 * 150 * 150));
        for (const rp of ripples) {
          const d = Math.abs(Math.abs(x - rp.x) - rp.r);
          v += A * 1.2 * Math.exp(-(d * d) / (2 * 28 * 28)) * (1 - rp.r / 420) * Math.exp(-((y0 - rp.y) ** 2) / (2 * 220 * 220));
        }
        x ? ctx.lineTo(x, y0 - v) : ctx.moveTo(x, y0 - v);
      }
      ctx.strokeStyle = `rgba(${rgb},${0.34 - r * 0.08})`; ctx.lineWidth = 1.8; ctx.lineJoin = "round"; ctx.stroke();
    }
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    if (pulses) drawTraces();
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j], d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < link) { ctx.strokeStyle = `rgba(${rgb},${0.22 * (1 - d / link)})`; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke(); }
      }
      if (mouse.on) {
        const d = Math.hypot(a.x - mouse.x, a.y - mouse.y);
        if (d < 170) { ctx.strokeStyle = `rgba(${rgb},${0.5 * (1 - d / 170)})`; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(mouse.x, mouse.y); ctx.stroke(); }
      }
    }
    for (const p of nodes) { ctx.fillStyle = `rgba(${rgb},.55)`; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 6.283); ctx.fill(); }
    for (const r of ripples) { ctx.strokeStyle = `rgba(${rgb},${0.35 * (1 - r.r / 420)})`; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(r.x, r.y, r.r, 0, 6.283); ctx.stroke(); }
  }

  function loop() { if (!visible || document.hidden) { raf = 0; return; } step(); draw(); raf = requestAnimationFrame(loop); }
  const start = () => { if (!raf && !calm) raf = requestAnimationFrame(loop); };

  const pos = (e) => { const r = host.getBoundingClientRect(); mouse.x = e.clientX - r.left; mouse.y = e.clientY - r.top; mouse.on = true; };
  host.addEventListener("pointermove", pos, { passive: true });
  host.addEventListener("pointerleave", () => { mouse.on = false; });
  host.addEventListener("pointerdown", (e) => { pos(e); ripples.push({ x: mouse.x, y: mouse.y, r: 0 }); });
  new ResizeObserver(size).observe(host);
  new IntersectionObserver((es) => { visible = es[0].isIntersecting; if (visible) start(); }).observe(host);
  document.addEventListener("visibilitychange", start);
  size(); start();
}
