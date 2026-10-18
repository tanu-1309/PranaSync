import { h, clear, api, forgetCache, ApiError, logo, tip, fmtDate } from "./ui.js";
import { loginView } from "./login.js";
import { overviewView, timelineView, labsView, medsView, historyView, helpView, qualityView } from "./record.js";
import { methodView, evidenceView } from "./method.js";

const app = document.getElementById("app");
const IDLE_MS = 20 * 60 * 1000;

let me = null;           // the signed-in patient's record, held in memory only
let idleTimer = null;
let mode = "patient";
try { mode = localStorage.getItem("prana-mode") || "patient"; } catch { /* ignore */ }

const prefersDark = () => matchMedia("(prefers-color-scheme: dark)").matches;
const isDark = () => (document.documentElement.dataset.theme || (prefersDark() ? "dark" : "light")) === "dark";
function toggleTheme(btn) {
  const next = isDark() ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("prana-theme", next); } catch { /* ignore */ }
  btn.textContent = next === "dark" ? "Light mode" : "Dark mode";
}

// ------------------------------------------------------------------ session
function showLogin(notice) {
  me = null; forgetCache(); clearTimeout(idleTimer);
  document.title = "Sign in · PranaChain Insight";
  history.replaceState(null, "", location.pathname);
  loginView(app, { notice, onSuccess: boot });
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
    if (e instanceof ApiError && e.status === 401) { showLogin(); return; }
    clear(app); app.append(h("p", { style: { padding: "40px" } }, "The portal can’t reach the server right now. Please try again in a moment."));
    return;
  }
  armIdle();
  shell();
  route();
}

// ------------------------------------------------------------------ shell
const NAV = [
  ["", "Overview", "01"], ["timeline", "Timeline", "02"], ["labs", "Labs and cycles", "03"], ["medications", "Medications", "04"],
  ["history", "History and notes", "05"], ["help", "What would help", "06"], ["quality", "Data quality", "07"],
];
const ABOUT = [["method", "How it works"], ["evidence", "The evidence"]];
let content, navEl, runhead;

function shell() {
  const asksN = me.scenarios.reduce((a, sc) => a + sc.missing_data.length, 0);
  const themeBtn = h("button", { onclick: (e) => toggleTheme(e.currentTarget) }, isDark() ? "Light mode" : "Dark mode");
  navEl = h("nav", { "aria-label": "Sections" },
    NAV.map(([k, label, n]) => h("a", { href: `#/${k}`, "data-k": k }, h("i", null, n), label, k === "help" && asksN ? h("span", { class: "cnt" }, asksN) : null)),
    h("hr"), h("div", { class: "cap" }, "About"),
    ABOUT.map(([k, label]) => h("a", { href: `#/${k}`, "data-k": k }, h("i", null, "·"), label)));
  const rail = h("aside", { class: "rail" },
    h("a", { class: "wordmark", href: "#/", "aria-label": "PranaChain Insight, overview" }, logo(34), h("div", null, h("b", null, "PranaChain"), h("small", null, "Insight"))),
    navEl,
    h("div", { class: "who" }, "Signed in as", h("b", null, me.id), h("div", { class: "row" }, h("button", { onclick: () => signOut() }, "Sign out"), themeBtn)));

  const seg = h("div", { class: "tog", role: "group", "aria-label": "Reading level" }, [["patient", "Plain language"], ["clinician", "Clinician view"]].map(([m, l]) =>
    h("button", { "aria-pressed": String(mode === m), onclick: () => {
      mode = m; try { localStorage.setItem("prana-mode", m); } catch { /* ignore */ }
      seg.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.textContent === l)));
      route();
    } }, l)));
  runhead = h("div", { class: "runhead" },
    h("span", null, `RECORD ${me.id} · ${fmtDate(me.window[0])} – ${fmtDate(me.window[1])} · ${me.profile.age} yrs · ${me.profile.sex}`),
    h("div", { class: "rt" }, seg, h("button", { class: "pr", onclick: () => window.print() }, "Print or save as PDF")));
  content = h("main", { class: "content", id: "main", tabindex: "-1" }, runhead);
  clear(app);
  app.append(h("div", { class: "shell" }, rail, content));
}

// ------------------------------------------------------------------ routes
const VIEWS = {
  "": () => overviewView(me, mode), timeline: () => timelineView(me), labs: () => labsView(me), medications: () => medsView(me),
  history: () => historyView(me), help: () => helpView(me), quality: () => qualityView(me), method: () => methodView(), evidence: () => evidenceView(),
};
const TITLES = { "": "Overview", timeline: "Timeline", labs: "Labs and cycles", medications: "Medications", history: "History and notes", help: "What would help", quality: "Data quality", method: "How it works", evidence: "The evidence" };

async function route() {
  if (!me) return;
  tip.hide();
  const key = location.hash.replace(/^#\/?/, "").split("/")[0];
  const k = key in VIEWS ? key : "";
  navEl.querySelectorAll("a").forEach((a) => (a.dataset.k === k ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
  runhead.querySelector(".tog").style.visibility = k === "" ? "visible" : "hidden";
  document.title = `${TITLES[k]} · PranaChain Insight`;
  [...content.children].slice(1).forEach((n) => n.remove());
  const view = await VIEWS[k]();
  if ((location.hash.replace(/^#\/?/, "").split("/")[0] in VIEWS ? location.hash.replace(/^#\/?/, "").split("/")[0] : "") !== k) return; // navigated away meanwhile
  content.append(view);
  window.scrollTo(0, 0);
}
addEventListener("hashchange", route);
boot();
