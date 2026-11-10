import { h, clear, api, forgetCache, ApiError, logo, tip, fmtDate } from "./ui.js";
import { loginView } from "./login.js";
import { landingView } from "./landing.js";
import { overviewView, timelineView, labsView, medsView, historyView, helpView, qualityView } from "./record.js";
import { accountView } from "./account.js";
import { outlookView } from "./outlook.js";
import { pageFx } from "./hero.js";
import { enhance, glow } from "./fx.js";
import { mountChat } from "./chat.js";
import { methodView, evidenceView } from "./method.js";

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
  loginView(app, { notice, onSuccess: boot, onBack: showLanding });
}
function showLanding() {
  me = null; forgetCache(); clearTimeout(idleTimer);
  history.replaceState(null, "", location.pathname);
  landingView(app, {
    onSignIn: () => showLogin(),
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
}

// ------------------------------------------------------------------ shell
const NAV = [["", "Home"], ["timeline", "Trends"], ["labs", "Labs"], ["medications", "Medicines"], ["outlook", "Outlook"]];
const MORE = [["history", "History and notes"], ["help", "What would help"], ["quality", "Data quality"], ["method", "How it works"], ["evidence", "The evidence"], ["account", "Account"]];
let content, navEl, runhead;

function shell() {
  const asksN = me.scenarios.reduce((a, sc) => a + sc.missing_data.length, 0);
  const themeBtn = h("button", { type: "button", onclick: (e) => toggleTheme(e.currentTarget) }, isDark() ? "Light mode" : "Dark mode");
  const more = h("details", { class: "menu navmore" }, h("summary", null, "More", asksN ? h("span", { class: "cnt" }, asksN) : null),
    h("div", { class: "pop" }, MORE.filter(([k]) => !(me.guest && k === "account")).map(([k, label]) => h("a", { href: `#/${k}`, "data-k": k }, label, k === "help" && asksN ? h("span", { class: "cnt" }, asksN) : null))));
  navEl = h("nav", { "aria-label": "Sections" }, NAV.map(([k, label]) => h("a", { href: `#/${k}`, "data-k": k }, label)), more);
  const user = h("details", { class: "menu user" }, h("summary", { "aria-label": "Account menu" }, h("span", { class: "dot" }, me.guest ? "G" : me.id.slice(-2)), h("span", { class: "who-t" }, me.guest ? "Sample record" : me.id)),
    h("div", { class: "pop right" },
      h("div", { class: "pi" }, me.guest ? "Looking around" : "Signed in as", h("b", null, me.guest ? "Sample record" : me.id), h("small", null, `${me.profile.age} yrs · ${me.profile.sex}`)),
      h("button", { type: "button", onclick: () => window.print() }, "Print or save as PDF"), themeBtn,
      h("button", { type: "button", onclick: () => signOut() }, me.guest ? "Exit sample" : "Sign out")));
  const top = h("header", { class: "topbar" },
    h("a", { class: "wordmark", href: "#/", "aria-label": "PranaSync, home" }, logo(36), h("b", null, "PranaSync")),
    navEl,
    h("div", { class: "tb-right" }, h("button", { class: "cta solid sm", type: "button", onclick: () => document.querySelector(".chat-fab")?.click() }, "Chat with Prana"), user));
  document.addEventListener("click", (e) => document.querySelectorAll("details.menu[open]").forEach((d) => { if (!d.contains(e.target)) d.removeAttribute("open"); }));
  addEventListener("hashchange", () => document.querySelectorAll("details.menu[open]").forEach((d) => d.removeAttribute("open")));

  const seg = h("div", { class: "tog", role: "group", "aria-label": "Reading level" }, [["patient", "Plain language"], ["clinician", "Clinician view"]].map(([m, l]) =>
    h("button", { "aria-pressed": String(mode === m), onclick: () => {
      mode = m; try { localStorage.setItem("prana-mode", m); } catch { /* ignore */ }
      seg.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.textContent === l)));
      route();
    } }, l)));
  runhead = h("div", { class: "runhead" }, h("span", null, `Record ${me.id} · ${fmtDate(me.window[0])} – ${fmtDate(me.window[1])}`), h("div", { class: "rt" }, seg));
  content = h("main", { class: "content", id: "main", tabindex: "-1" }, runhead);
  if (me.guest) content.append(h("div", { class: "guestbar" }, h("span", null, "You’re viewing a ", h("b", null, "sample record"), " in guest mode, a way to look around without an account."), h("button", { onclick: () => signOut() }, "Sign in with my ID")));
  clear(app);
  app.append(h("div", { class: "shell" }, top, content));
  mountChat(app);
  glow(app);
}

// ------------------------------------------------------------------ routes
const VIEWS = {
  "": () => overviewView(me, mode), timeline: () => timelineView(me), labs: () => labsView(me), medications: () => medsView(me), outlook: () => outlookView(me),
  history: () => historyView(me), account: () => accountView(me, {}), help: () => helpView(me), quality: () => qualityView(me), method: () => methodView(), evidence: () => evidenceView(),
};
const TITLES = { "": "Overview", timeline: "Timeline", labs: "Labs and cycles", medications: "Medications", outlook: "Outlook", account: "Account", history: "History and notes", help: "What would help", quality: "Data quality", method: "How it works", evidence: "The evidence" };

async function route() {
  if (!me) return;
  tip.hide();
  const key = location.hash.replace(/^#\/?/, "").split("/")[0];
  const k = key in VIEWS ? key : "";
  navEl.querySelectorAll("a").forEach((a) => (a.dataset.k === k ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
  navEl.querySelector("details.navmore > summary")?.classList.toggle("on", !!navEl.querySelector("details.navmore a[aria-current]"));
  runhead.querySelector(".tog").style.visibility = k === "" ? "visible" : "hidden";
  document.title = `${TITLES[k]} · PranaSync`;
  [...content.children].filter((n) => n !== runhead && !n.classList.contains("guestbar")).forEach((n) => n.remove());
  const view = await VIEWS[k]();
  if ((location.hash.replace(/^#\/?/, "").split("/")[0] in VIEWS ? location.hash.replace(/^#\/?/, "").split("/")[0] : "") !== k) return; // navigated away meanwhile
  content.append(view);
  enhance(view);
  window.scrollTo(0, 0);
}
addEventListener("hashchange", route);
addEventListener("beforeprint", () => document.querySelectorAll("details").forEach((d) => { d.open = true; }));
pageFx();
boot();
