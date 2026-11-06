import { h, clear, api, forgetCache, ApiError, logo, tip, fmtDate, icon } from "./ui.js";
import { loginView } from "./login.js";
import { landingView } from "./landing.js";
import { overviewView } from "./record.js";
import { accountView } from "./account.js";
import { recordsView, insightsView, howView, RECORD_TABS, HOW_TABS, INSIGHT_LABELS } from "./hubs.js";
import { startAI } from "./ai.js";
import { pageFx } from "./hero.js";
import { enhance, glow } from "./fx.js";
import { mountChat } from "./chat.js";
import { uploadView, uploadsHome } from "./risk.js";
import { registerView } from "./register.js";
import { reviewView } from "./review.js";
import { adminView } from "./admin.js";
import { clinicalView } from "./clinical.js";

const app = document.getElementById("app");
const IDLE_MS = 20 * 60 * 1000;

let me = null;           // the signed-in patient's record, held in memory only
let idleTimer = null;
let mode = "patient";
try { mode = localStorage.getItem("prana-mode") || "patient"; } catch { /* ignore */ }

const isDark = () => document.documentElement.dataset.theme === "dark";
function toggleTheme(btn) {
  const next = isDark() ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("prana-theme", next); } catch { /* ignore */ }
  btn.textContent = next === "dark" ? "Light mode" : "Dark mode";
}

// ------------------------------------------------------------------ session
function showLogin(notice) {
  me = null; forgetCache(); clearTimeout(idleTimer);
  document.title = "Sign in · PranaSync";
  history.replaceState(null, "", location.pathname);
  loginView(app, { notice, onSuccess: boot, onBack: showLanding, onRegister: showRegister });
}
function showRegister() {
  me = null; forgetCache(); clearTimeout(idleTimer);
  document.title = "Create account · PranaSync";
  registerView(app, { onSuccess: boot, onBack: showLanding, onSignIn: () => showLogin() });
}
function showLanding() {
  me = null; forgetCache(); clearTimeout(idleTimer);
  history.replaceState(null, "", location.pathname);
  landingView(app, {
    onSignIn: () => showLogin(), onRegister: showRegister,
    onGuest: async () => { try { await api("guest", { method: "POST" }); boot(); } catch { showLogin("The sample record is not available right now."); } },
  });
}
async function signOut(notice) {
  try { await api("logout", { method: "POST" }); } catch { /* already gone */ }
  showLogin(notice);
}
function armIdle() {
  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => signOut("You were signed out after 20 minutes of inactivity."), IDLE_MS);
}
["pointerdown", "keydown", "scroll"].forEach((ev) => addEventListener(ev, () => { if (me) armIdle(); }, { passive: true }));

async function boot() {
  try { me = await api("me", { fresh: true }); }
  catch (e) {
    if (e instanceof ApiError && e.status === 401) { showLanding(); return; }
    clear(app); app.append(h("p", { style: { padding: "40px" } }, "The portal can’t reach the server right now. Please try again in a moment."));
    return;
  }
  armIdle();
  shell();
  route();
  if (me.mode === "uploads") return;   // someone who builds their record by uploading documents has no workbook for the AI text to describe
  const loadAI = () => startAI(me, () => { if (me) route(); });
  document.addEventListener("prana:retry-ai", loadAI);
  loadAI();
}

// ------------------------------------------------------------------ shell
// Five places, always the same, for everyone. Everything else is a tab inside one of them, or a page reached from a button.
const NAV_FULL = [["", "Home"], ["records", "Trends and labs"], ["insights", "Analytics and outlook"], ["how", "How it works"], ["account", "Account"]];
const NAV_UPLOADS = [["", "Home"], ["insights", "Analytics and outlook"], ["how", "How it works"], ["account", "Account"]];
let content, navEl, runhead, announcer;
const NAV = () => (me.mode === "uploads" ? NAV_UPLOADS : NAV_FULL);

function shell() {
  const asksN = me.scenarios.reduce((a, sc) => a + sc.missing_data.length, 0);
  const themeBtn = h("button", { type: "button", onclick: (e) => toggleTheme(e.currentTarget) }, isDark() ? "Light mode" : "Dark mode");
  navEl = h("nav", { "aria-label": "Main" }, NAV().map(([k, label]) => h("a", { href: `#/${k}`, "data-k": k }, label, k === "insights" && asksN ? h("span", { class: "cnt", "aria-label": `${asksN} suggestions` }, asksN) : null)));
  const user = h("details", { class: "menu user" }, h("summary", { "aria-label": "Account menu" }, h("span", { class: "dot" }, me.guest ? "G" : me.id.slice(-2)), h("span", { class: "who-t" }, me.guest ? "Sample record" : me.id)),
    h("div", { class: "pop right" },
      h("div", { class: "pi" }, me.guest ? "Looking around" : "Signed in as", h("b", null, me.guest ? "Sample record" : me.id), h("small", null, [me.profile.age != null ? `${Math.round(me.profile.age)} yrs` : null, me.profile.sex].filter(Boolean).join(" · ") || "No details yet")),
      h("button", { type: "button", onclick: () => window.print() }, "Print or save as PDF"), themeBtn,
      h("button", { type: "button", onclick: () => signOut() }, me.guest ? "Exit sample" : "Sign out")));
  const top = h("header", { class: "topbar" },
    h("a", { class: "wordmark", href: "#/", "aria-label": "PranaSync, home" }, logo(36), h("b", null, "PranaSync")),
    navEl,
    h("div", { class: "tb-right" }, h("a", { class: "cta solid sm", href: "#/upload" }, icon("upload", 16), "Upload documents"), user));
  document.addEventListener("click", (e) => document.querySelectorAll("details.menu[open]").forEach((d) => { if (!d.contains(e.target)) d.removeAttribute("open"); }));
  addEventListener("hashchange", () => document.querySelectorAll("details.menu[open]").forEach((d) => d.removeAttribute("open")));

  const seg = h("div", { class: "tog", role: "group", "aria-label": "Reading level" }, [["patient", "Plain language"], ["clinician", "Clinician view"]].map(([m, l]) =>
    h("button", { "aria-pressed": String(mode === m), onclick: () => {
      mode = m; try { localStorage.setItem("prana-mode", m); } catch { /* ignore */ }
      seg.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.textContent === l)));
      route();
    } }, l)));
  runhead = h("div", { class: "runhead" }, h("span", null, `Record ${me.id} · ${fmtDate(me.window[0])} – ${fmtDate(me.window[1])}`), h("div", { class: "rt" }, seg));
  announcer = h("div", { class: "sr", role: "status", "aria-live": "polite" });
  content = h("main", { class: "content", id: "main", tabindex: "-1" }, runhead, announcer);
  if (me.guest) content.append(h("div", { class: "guestbar" }, h("span", null, "You’re viewing a ", h("b", null, "sample record"), " in guest mode, a way to look around without an account."), h("button", { onclick: () => signOut() }, "Sign in with my ID")));
  clear(app);
  app.append(h("div", { class: "shell" }, top, content));
  if (me.mode !== "uploads") mountChat(app);
  glow(app);
}

// ------------------------------------------------------------------ routes
// Old addresses (from links, bookmarks and chat answers) still work: they open the right tab.
const ALIAS = { timeline: ["records", "trends"], labs: ["records", "labs"], medications: ["records", "medicines"], history: ["records", "history"],
  outlook: ["insights", "outlook"], analytics: ["insights", "analytics"], help: ["insights", "help"], method: ["how", "method"], evidence: ["how", "evidence"],
  statistics: ["clinical", "statistics"], quality: ["clinical", "quality"] };
const PARENT = { clinical: "insights", upload: "", review: "", admin: "account" };   // pages reached by a button: the menu keeps the section they belong to lit
const SUBS = { records: Object.fromEntries(RECORD_TABS), how: Object.fromEntries(HOW_TABS), insights: INSIGHT_LABELS };
const asksCount = () => me.scenarios.reduce((a, sc) => a + sc.missing_data.length, 0);

// Easy back and forth. Pages reached from a button (Upload, Statistical findings, Data quality) say exactly where "back" goes: the page you came from, not a fixed one.
// The browser's Back button works too, and returns you to the same place on the page you left.
let lastMain = null;       // the last page that is a place in the menu (or a tab of one)
let cameFrom = null;       // what lastMain was when the current button page opened
const placeLabel = (t) => `${TITLES[t.k]}${SUBS[t.k]?.[t.sub] ? `: ${SUBS[t.k][t.sub]}` : ""}`;
function withBack(view, fallbackHash, fallbackLabel, fixed = false) {
  const t = fixed ? null : cameFrom, href = t ? t.hash : fallbackHash, label = t ? placeLabel(t) : fallbackLabel;
  const a = h("a", { class: "backlink", href }, "← Back to ", label);
  return Promise.resolve(view).then((v) => { v.prepend(a); return v; });
}

const VIEWS_UPLOADS = { "": () => uploadsHome(me), upload: () => withBack(uploadView(me), "#/", "Home"), review: (sub) => withBack(reviewView(me, sub), "#/upload", "Upload documents", true), insights: (sub) => insightsView(me, sub), clinical: (sub) => withBack(clinicalView(me, sub), "#/insights/outlook", "Analytics and outlook"), how: (sub) => howView(me, sub), account: () => accountView(me, {}) };
const VIEWS_FULL = {
  "": () => overviewView(me, mode), upload: () => withBack(uploadView(me), "#/", "Home"), review: (sub) => withBack(reviewView(me, sub), "#/upload", "Upload documents", true), admin: () => withBack(adminView(me), "#/account", "Account", true), records: (sub) => recordsView(me, sub), insights: (sub) => insightsView(me, sub, asksCount()), how: (sub) => howView(me, sub),
  account: () => accountView(me, {}), clinical: (sub) => withBack(clinicalView(me, sub), "#/insights/outlook", "Analytics and outlook"),
};
const VIEWS = new Proxy({}, { get: (_, k) => (me?.mode === "uploads" ? VIEWS_UPLOADS : VIEWS_FULL)[k], has: (_, k) => k in (me?.mode === "uploads" ? VIEWS_UPLOADS : VIEWS_FULL) });
const TITLES = { "": "Home", records: "Trends and labs", insights: "Analytics and outlook", how: "How it works", account: "Account", upload: "Upload documents", review: "Review document", admin: "Administration", clinical: "Clinical view" };

function where() {
  const [a, b] = location.hash.replace(/^#\/?/, "").split("/");
  const [k, sub] = ALIAS[a] ? [ALIAS[a][0], b || ALIAS[a][1]] : [a || "", b || ""];
  return { k: k in VIEWS ? k : "", sub };
}

// Was this arrival a click on a link, or the browser's Back/Forward? Only the second restores the old scroll position.
let viaLink = false, curHash = null, first = true;
const scrollAt = new Map();
document.addEventListener("click", (e) => { if (e.target.closest?.('a[href^="#/"]')) { viaLink = true; setTimeout(() => { viaLink = false; }, 400); } }, true);

let routeSeq = 0;   // the newest call wins: the app asks for a redraw several times while it starts, and an older, slower draw must not add a second copy of the page
async function route() {
  if (!me) return;
  const mine = ++routeSeq;
  tip.hide();
  const hash = location.hash || "#/";
  const sameAsBefore = hash === curHash;                           // a redraw of the page you are on (for example when the AI text arrives): stay where you are
  const traversal = !viaLink && !sameAsBefore && !first;           // Back or Forward
  if (curHash && !sameAsBefore) scrollAt.set(curHash, scrollY);
  const keepY = sameAsBefore ? scrollY : traversal ? scrollAt.get(hash) : undefined;
  viaLink = false;
  const { k, sub } = where();
  if (!(k in PARENT)) { cameFrom = lastMain; lastMain = { k, sub, hash }; } else if (!sameAsBefore) cameFrom = lastMain;
  const lit = k in PARENT ? PARENT[k] : k;
  navEl.querySelectorAll("a").forEach((a) => (a.dataset.k === lit ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
  runhead.querySelector(".tog").style.visibility = k === "" && me.mode !== "uploads" ? "visible" : "hidden";
  document.title = `${TITLES[k]} · PranaSync`;
  [...content.children].filter((n) => n !== runhead && n !== announcer && !n.classList.contains("guestbar")).forEach((n) => n.remove());
  const view = await VIEWS[k](sub);
  if (mine !== routeSeq) return;
  if (where().k !== k) return; // navigated away meanwhile
  content.append(view);
  enhance(view);
  announcer.textContent = `${TITLES[k]}`;
  curHash = hash;
  const settle = (y) => { window.scrollTo(0, y); [500, 1400].forEach((ms) => setTimeout(() => { if (mine === routeSeq && Math.abs(scrollY - y) > 4 && scrollY < 40) window.scrollTo(0, y); }, ms)); };
  if (keepY != null) settle(keepY);
  else {
    window.scrollTo(0, 0);
    if (!first) { const hd = view.querySelector("h1"); if (hd) { hd.tabIndex = -1; hd.focus({ preventScroll: true }); } }   // a keyboard or screen-reader user lands on the new page's heading
  }
  first = false;
}
addEventListener("hashchange", route);
addEventListener("beforeprint", () => document.querySelectorAll("details").forEach((d) => { d.open = true; }));
pageFx();
boot();
