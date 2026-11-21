# ruff: noqa: E702
"""End-to-end browser tests: a real browser drives the real portal the way a person would.

Slow, so they run only on request:

    RUN_E2E=1 python -m pytest tests/test_e2e.py -q          (Windows PowerShell:  $env:RUN_E2E=1; python -m pytest tests/test_e2e.py -q)

Needs `pip install playwright` and a browser (`playwright install chromium`, or Microsoft Edge/Chrome already on the computer).
The server runs on a free local port with throwaway databases and test accounts; nothing touches real data, and no AI model is called.
"""
import io
import os
import socket
import threading
import time

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

from prana.api import auth, risk_routes, server  # noqa: E402
from prana.data import db, docstore  # noqa: E402
from prana.risk import model, ocr  # noqa: E402

pytestmark = pytest.mark.skipif(os.getenv("RUN_E2E") != "1", reason="set RUN_E2E=1 to run the browser tests")
PW = "alpha-beta-gamma-11"
NAV = ["Home", "Trends and labs", "Analytics and outlook", "How it works", "Account"]
# address -> something its page must say
PAGES = {"records/trends": "Trends and labs", "records/labs": "Trends and labs", "records/medicines": "Trends and labs", "records/history": "Trends and labs",
         "insights/outlook": "Analytics and outlook", "insights/analytics": "Summary and graphs", "insights/help": "Analytics and outlook",
         "how/models": "How it works", "how/architecture": "What happens when you upload", "how/method": "Five steps, end to end", "how/evidence": "How we know the pipeline behaves",
         "clinical/statistics": "Clinical view", "clinical/values": "Baseline comparison", "clinical/risk": "Clinical view", "clinical/documents": "Clinical view",
         "clinical/medicines": "Medicines on record", "clinical/quality": "Clinical view", "account": "Your details", "upload": "Upload documents"}
OLD = {"timeline": "Trends", "labs": "Labs", "medications": "Medicines", "outlook": "Outlook", "history": "History and notes", "help": "What would help", "analytics": "Analytics and intelligence",
       "method": "How patterns are found", "evidence": "Evidence and limits", "statistics": "Statistical findings", "quality": "Data quality"}
LAB_OLD = b"Report date: 12 September 2026\nAge: 58\nSex: Male\nFasting glucose 148 mg/dL\nHbA1c: 7.1 %\nLDL cholesterol 162 mg/dL\nBlood pressure: 152/94 mmHg\n"
LAB_NEW = b"Report date: 12 November 2026\nFasting glucose 132 mg/dL\nHbA1c: 6.7 %\nLDL cholesterol 141 mg/dL\n"


@pytest.fixture(scope="module")
def site(workbooks, tmp_path_factory):
    import uvicorn
    mp = pytest.MonkeyPatch()
    tmp = tmp_path_factory.mktemp("e2e")
    mp.setattr(server, "_index", lambda: {"T2D": workbooks["t2d"], "HTN": workbooks["htn"]})
    mp.setattr(server, "GUEST_ID", "T2D")
    eng = create_engine(f"sqlite:///{tmp / 'e2e.db'}", future=True, connect_args={"check_same_thread": False})
    mp.setattr(db, "_engine", eng)
    db.init_db()
    docs = create_engine(f"sqlite:///{tmp / 'documents.db'}", future=True, connect_args={"check_same_thread": False})
    docstore.use_engine(docs)
    mp.setattr(docstore, "KEY_FILE", tmp / "key")
    mp.setattr(risk_routes, "UPLOAD_DIR", tmp / "uploads")
    db.set_user_hashes({"T2D": auth.hash_password(PW), "HTN": auth.hash_password(PW)})
    mp.setattr(auth, "_fails", {})
    server._risk.hits.clear()
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    srv = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    mp.undo(); eng.dispose(); docs.dispose()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        for kw in ({}, {"channel": "msedge"}, {"channel": "chrome"}):
            try:
                b = p.chromium.launch(**kw)
                break
            except Exception:  # noqa: BLE001
                b = None
        if b is None:
            pytest.skip("no browser available (run: playwright install chromium)")
        yield b
        b.close()


@pytest.fixture()
def page(browser, site):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(f"pageerror: {e}"))
    pg.on("console", lambda m: pg.errors.append(f"console: {m.text}") if m.type == "error" and "401" not in m.text and "Unauthorized" not in m.text and "404" not in m.text else None)
    yield pg
    ctx.close()


def register(pg, site, name="Test Person"):
    pg.goto(site); pg.click("text=Create account >> nth=0"); pg.wait_for_selector("#rg-pw")
    pg.fill("#rg-name", name); pg.fill("#rg-pw", "a-long-demo-password-1"); pg.fill("#rg-pw2", "a-long-demo-password-1")
    pg.click("text=Create my account"); pg.wait_for_selector(".steps", timeout=15000)


def upload(pg, site, data, name):
    pg.goto(f"{site}/#/upload"); pg.wait_for_selector(".up-drop")
    pg.set_input_files("#up-file", {"name": name, "mimeType": "application/octet-stream", "buffer": data})
    pg.wait_for_selector(".review .rv-table", timeout=60000)


def test_landing_then_sample_record_then_five_places_and_every_page(page, site):
    page.goto(site)
    page.wait_for_selector(".lp-hero h1")
    assert page.locator("canvas.bg-canvas").count() >= 1                      # the moving background mounted
    page.click("text=Try the sample record")
    page.wait_for_selector(".topbar")
    assert page.locator(".guestbar").count() == 1
    assert [a.inner_text().split("\n")[0].strip() for a in page.locator(".topbar nav a").all()] == NAV      # five places, always the same
    assert page.locator(".tb-right >> text=Chat with Prana").count() == 0     # the top bar has Upload, not Chat
    page.wait_for_selector("#glance"); page.wait_for_selector("#levels-home"); page.wait_for_selector("#care-home")
    for route, expect in PAGES.items():
        page.goto(f"{site}/#/{route}")
        page.wait_for_selector(".page")
        page.wait_for_function("document.querySelector('.page').innerText.length > 40")
        page.wait_for_timeout(300)
        assert expect.lower() in page.inner_text(".page").lower(), route
    assert page.errors == []


def test_old_addresses_still_open_the_right_tab(page, site):
    page.goto(site); page.click("text=Try the sample record"); page.wait_for_selector(".topbar")
    for old, tab in OLD.items():
        page.goto(f"{site}/#/{old}")
        page.wait_for_selector(".page")
        page.wait_for_timeout(200)
        assert page.locator(".tabs .tab[aria-current=page]").first.inner_text().split("\n")[0].strip() == tab, old
    assert page.errors == []


def test_chat_says_when_the_ai_is_unavailable_and_still_refuses_unsafe_questions(page, site):   # the model is off in this test site
    page.goto(site); page.click("text=Try the sample record"); page.wait_for_selector(".topbar")
    page.click(".chat-fab")
    page.wait_for_selector(".chat-sugg button")

    def ask(question):
        """Send one question and wait for its own reply (the box ignores a new question while one is being answered), then return that reply's text."""
        before = page.locator(".msg.bot:not(.typing)").count()
        page.fill(".chat-panel input", question)
        page.press(".chat-panel input", "Enter")
        page.wait_for_function("n => document.querySelectorAll('.msg.bot:not(.typing)').length > n && !document.querySelector('.msg.bot.typing')", arg=before, timeout=15000)
        return page.locator(".msg.bot:not(.typing)").last.inner_text()

    assert "clinical view" in ask("What are the chances of me getting a heart attack?")      # no model: an honest message, no template answer
    assert "emergency number" in ask("I have chest pain")
    assert "can’t advise on medicines" in ask("Should I stop my medicine?")
    assert page.errors == []


def test_sign_in_changes_the_password_and_signs_out(page, site):
    page.goto(site)
    page.click(".lp-nav >> text=Sign in")
    page.wait_for_selector("form")
    page.fill("#pid", "T2D"); page.fill("#pwd", PW)
    page.click("button[type=submit]")
    page.wait_for_selector(".topbar")
    assert page.locator(".guestbar").count() == 0                              # a signed-in patient is not in guest mode
    page.goto(f"{site}/#/account")
    page.wait_for_selector("#ac-security"); page.click("text=Change your password")
    page.fill("#cur", PW); page.fill("#new", "a-brand-new-password-9"); page.fill("#again", "a-brand-new-password-9")
    page.click(".pwform >> text=Change password")
    page.wait_for_selector(".pwform .ac-msg.ok", timeout=8000)
    page.click(".user > summary"); page.click("text=Sign out")
    page.wait_for_selector("text=Welcome back")                                # signing out returns to the sign-in page
    assert page.errors == []


def test_wrong_password_is_refused_and_looks_the_same_as_an_unknown_id(page, site):
    page.goto(site); page.click(".lp-nav >> text=Sign in"); page.wait_for_selector("form")
    page.fill("#pid", "HTN"); page.fill("#pwd", "not-the-password"); page.click("button[type=submit]")
    page.wait_for_selector("#err >> text=don’t match")
    page.fill("#pid", "NOBODY"); page.fill("#pwd", "whatever-it-is"); page.click("button[type=submit]")
    page.wait_for_selector("#err >> text=don’t match")


def test_register_upload_review_correct_and_see_how_values_changed(page, site):
    register(page, site)
    assert [a.inner_text().split("\n")[0].strip() for a in page.locator(".topbar nav a").all()] == ["Home", "Analytics and outlook", "How it works", "Account"]
    upload(page, site, LAB_OLD, "september.txt")                              # always lands on the review page
    assert page.locator(".rv-chip.todo").count() == 1 and "Needs your check" in page.inner_text(".rv-meta")
    assert page.locator(".backlink").inner_text().endswith("Back to Upload documents")
    page.fill("#rv-hba1c", "7.0")
    page.click("text=Save and confirm these values")
    page.wait_for_selector(".rv-msg.ok", timeout=15000)
    assert "Checked by you" in page.inner_text(".rv-meta")
    page.click(".rv-msg >> text=Back to your documents")
    page.wait_for_selector(".up-row")
    assert "Checked by you" in page.inner_text(".up-row")
    upload(page, site, LAB_NEW, "november.txt")
    page.click("text=Save and confirm these values"); page.wait_for_selector(".rv-msg.ok", timeout=15000)
    page.goto(f"{site}/#/"); page.wait_for_selector("#history-home table", timeout=15000)
    row = page.locator("#history-home tr", has_text="HbA1c").inner_text()
    assert "7" in row and "6.7" in row and "lower" in row                      # the corrected 7.0 against the newer 6.7
    assert page.locator("#history-home svg.spark").count() >= 1
    if model.load() is not None:
        page.wait_for_selector(".rk-card:not(.skel)"); assert page.locator(".rk-card").count() == 3
    assert page.errors == []


def test_account_edit_unsaved_bar_and_back_links(page, site):
    register(page, site, "Back Forth")
    page.goto(f"{site}/#/account"); page.wait_for_selector("#pf-age")
    assert page.locator(".ac-savebar").is_hidden()
    page.fill("#pf-age", "47"); page.select_option("#pf-sex", "Female")
    assert page.locator(".ac-savebar").is_visible()
    page.click(".ac-savebar >> text=Save changes"); page.wait_for_selector(".ac-msg.ok", timeout=10000)
    page.fill("#pf-email", "not-an-email"); page.click(".ac-savebar >> text=Save changes"); page.wait_for_selector(".ac-msg.err >> text=Email")
    page.goto(f"{site}/#/account"); page.wait_for_selector("text=Upload or manage documents"); page.click("text=Upload or manage documents")
    page.wait_for_selector(".backlink")
    assert "Back to Account" in page.inner_text(".backlink")
    page.click(".backlink"); page.wait_for_selector("#ac-details")
    assert [e for e in page.errors if "422" not in e] == []             # the 422 is the refused bad email, on purpose


def test_clinical_view_shows_the_tables_and_a_back_link_to_where_you_came_from(page, site):
    page.goto(site); page.click("text=Try the sample record"); page.wait_for_selector(".topbar")
    page.goto(f"{site}/#/insights/analytics"); page.wait_for_selector(".an-more")
    page.click(".an-more >> text=Open the clinical view"); page.wait_for_selector(".backlink")
    assert "Back to Analytics and outlook: Analytics and intelligence" in page.inner_text(".backlink")
    assert [t.inner_text().split("\n")[0].strip() for t in page.locator(".tabs .tab").all()][:3] == ["Statistical findings", "Values and tables", "Risk model detail"]
    page.click(".tabs >> text=Values and tables"); page.wait_for_selector("table")
    assert page.locator("table").count() >= 3
    assert page.errors == []


@pytest.mark.skipif(not ocr.available(), reason="the on-device text reader is not installed")
def test_a_photo_of_a_report_is_read_and_its_values_are_marked_for_checking(page, site):
    from PIL import Image, ImageDraw, ImageFont
    font = None
    for name in ("consola.ttf", "DejaVuSansMono.ttf", "cour.ttf", "arial.ttf"):
        try:
            font = ImageFont.truetype(name, 26)
            break
        except OSError:
            continue
    im = Image.new("RGB", (1000, 300), "white"); d = ImageDraw.Draw(im)
    for i, ln in enumerate(["Report date: 12 September 2026", "Fasting glucose   148 mg/dL   (70-99)", "HbA1c   7.1 %   (4.0-5.6)", "Blood pressure: 152/94 mmHg"]):
        d.text((30, 30 + 50 * i), ln, fill=(30, 30, 30), font=font or ImageFont.load_default(size=26))
    buf = io.BytesIO(); im.save(buf, "PNG")
    register(page, site, "Photo Person")
    upload(page, site, buf.getvalue(), "photo.png")
    assert page.locator(".rv-ai >> text=Read from an image").count() >= 2 and "OCR" in page.inner_text(".rv-meta")
    assert page.errors == []


def test_the_page_works_on_a_phone_sized_screen(browser, site):
    ctx = browser.new_context(viewport={"width": 390, "height": 800}, is_mobile=True)
    pg = ctx.new_page()
    pg.goto(site); pg.wait_for_selector(".lp-hero h1")
    assert pg.evaluate("document.documentElement.scrollWidth") <= 392         # no sideways scrolling
    pg.click("text=Try the sample record"); pg.wait_for_selector(".topbar")
    for route in ("", "insights/outlook", "how/architecture", "account", "clinical/risk"):
        pg.goto(f"{site}/#/{route}"); pg.wait_for_selector(".page"); pg.wait_for_timeout(500)
        assert pg.evaluate("document.documentElement.scrollWidth") <= 392, route
    ctx.close()
