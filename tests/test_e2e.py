# ruff: noqa: E702
"""End-to-end browser tests: a real browser drives the real portal the way a patient would.

Slow, so they run only on request:

    RUN_E2E=1 python -m pytest tests/test_e2e.py -q          (Windows PowerShell:  $env:RUN_E2E=1; python -m pytest tests/test_e2e.py -q)

Needs `pip install playwright` and a browser (`playwright install chromium`, or Microsoft Edge/Chrome already on the computer).
The server runs on a free local port with a throwaway database and test accounts; nothing touches real data.
"""
import os
import socket
import threading
import time

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

from prana.api import auth, server  # noqa: E402
from prana.data import db  # noqa: E402

pytestmark = pytest.mark.skipif(os.getenv("RUN_E2E") != "1", reason="set RUN_E2E=1 to run the browser tests")
PW = "alpha-beta-gamma-11"
PAGES = {"timeline": "Timeline", "labs": "Labs", "medications": "Medications", "outlook": "Outlook", "history": "History", "help": "What would help", "quality": "Data quality",
         "method": "pattern needs company", "evidence": "Quiet when it should be"}


@pytest.fixture(scope="module")
def site(workbooks, tmp_path_factory):
    import uvicorn
    mp = pytest.MonkeyPatch()
    mp.setattr(server, "_index", lambda: {"T2D": workbooks["t2d"], "HTN": workbooks["htn"]})
    mp.setattr(server, "GUEST_ID", "T2D")
    eng = create_engine(f"sqlite:///{tmp_path_factory.mktemp('e2e') / 'e2e.db'}", future=True, connect_args={"check_same_thread": False})
    mp.setattr(db, "_engine", eng)
    db.init_db()
    db.set_user_hashes({"T2D": auth.hash_password(PW), "HTN": auth.hash_password(PW)})
    mp.setattr(auth, "_fails", {})
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
    mp.undo(); eng.dispose()


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
    pg.on("console", lambda m: pg.errors.append(f"console: {m.text}") if m.type == "error" and "401" not in m.text and "Unauthorized" not in m.text else None)
    yield pg
    ctx.close()


def test_landing_page_then_sample_record_then_every_page(page, site):
    page.goto(site)
    page.wait_for_selector(".lp-hero h1")
    assert "made clear" in page.inner_text(".lp-hero h1")
    assert page.locator("canvas.bg-canvas").count() >= 1                      # the moving background mounted
    page.click("text=Try the sample record")
    page.wait_for_selector(".topbar")
    assert page.locator(".guestbar").count() == 1
    assert page.locator(".glance .gl").count() >= 4                           # at-a-glance cards on Home
    for route, expect in PAGES.items():
        page.goto(f"{site}/#/{route}")
        page.wait_for_selector(".page")
        assert expect.lower() in page.inner_text(".page").lower(), route
    assert page.errors == []


def test_outlook_shows_both_risks_and_a_trend_for_each_measure_outside_range(page, site):
    page.goto(site); page.click("text=Try the sample record"); page.wait_for_selector(".topbar")
    page.goto(f"{site}/#/outlook")
    page.wait_for_selector(".riskgrid")
    assert page.locator(".risk").count() == 2
    assert page.locator(".watch").count() >= 1
    page.locator(".watch svg.fcchart").first.hover()                          # hovering a chart shows the value
    assert page.locator(".tip.on").count() == 1
    assert page.errors == []


def test_chatbot_answers_a_risk_question_and_refuses_unsafe_ones(page, site):
    page.goto(site); page.click("text=Try the sample record"); page.wait_for_selector(".topbar")
    page.click(".chat-fab")
    page.wait_for_selector(".chat-sugg button")
    page.fill(".chat-panel input", "What are the chances of me getting a heart attack?")
    page.press(".chat-panel input", "Enter")
    page.wait_for_selector(".msg.bot:not(.typing) >> text=in the next 10 years", timeout=8000)
    page.fill(".chat-panel input", "I have chest pain")
    page.press(".chat-panel input", "Enter")
    page.wait_for_selector("text=emergency number", timeout=8000)
    page.fill(".chat-panel input", "Should I stop my medicine?")
    page.press(".chat-panel input", "Enter")
    page.wait_for_selector("text=can’t advise on medicines", timeout=8000)
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
    page.wait_for_selector(".pwform")
    page.fill("#cur", PW); page.fill("#new", "a-brand-new-password-9"); page.fill("#again", "a-brand-new-password-9")
    page.click("text=Change password >> nth=-1")
    page.wait_for_selector(".pwform .ok", timeout=8000)
    page.click(".user > summary"); page.click("text=Sign out")
    page.wait_for_selector("text=Welcome back")                                # signing out returns to the sign-in page
    assert page.errors == []


def test_wrong_password_is_refused_and_looks_the_same_as_an_unknown_id(page, site):
    page.goto(site); page.click(".lp-nav >> text=Sign in"); page.wait_for_selector("form")
    page.fill("#pid", "HTN"); page.fill("#pwd", "not-the-password"); page.click("button[type=submit]")
    page.wait_for_selector("#err >> text=don’t match")
    page.fill("#pid", "NOBODY"); page.fill("#pwd", "whatever-it-is"); page.click("button[type=submit]")
    page.wait_for_selector("#err >> text=don’t match")


def test_the_page_works_on_a_phone_sized_screen(browser, site):
    ctx = browser.new_context(viewport={"width": 390, "height": 800}, is_mobile=True)
    pg = ctx.new_page()
    pg.goto(site); pg.wait_for_selector(".lp-hero h1")
    assert pg.evaluate("document.documentElement.scrollWidth") <= 392         # no sideways scrolling
    pg.click("text=Try the sample record"); pg.wait_for_selector(".topbar")
    assert pg.evaluate("document.documentElement.scrollWidth") <= 392
    ctx.close()
