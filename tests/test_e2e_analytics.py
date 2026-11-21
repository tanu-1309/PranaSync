# ruff: noqa: E702, F401, F811
"""Browser tests for the Analytics & Intelligence page, driven like a person would. Run with RUN_E2E=1 (see tests/test_e2e.py for what it needs)."""
import os

import pytest

pytest.importorskip("playwright.sync_api")
from test_e2e import browser, page, site  # noqa: E402  (the same throwaway server and browser fixtures)

pytestmark = pytest.mark.skipif(os.getenv("RUN_E2E") != "1", reason="set RUN_E2E=1 to run the browser tests")


@pytest.fixture(autouse=True)
def _fresh_limits():
    """Other test files use the same patient id within the same minute, so start each browser test with empty rate limiters (every page load also asks for the AI text, which is limited per minute)."""
    from prana.api import server
    server._analytics.hits.clear(); server._NARRATIVE_HITS.clear(); server._CHAT_HITS.clear()


def open_page(page, site):
    page.goto(site); page.click("text=Try the sample record"); page.wait_for_selector(".topbar")
    page.goto(f"{site}/#/analytics")
    page.wait_for_selector("#an-insights", timeout=15000)


def test_the_page_is_in_the_menu_and_is_short_and_in_order_with_nothing_repeated(page, site):
    open_page(page, site)
    page.click(".navmore > summary")
    assert page.locator(".navmore .pop a", has_text="Analytics & Intelligence").count() == 1
    page.keyboard.press("Escape")
    ids = page.eval_on_selector_all(".analytics .an-sec", "els => els.map(e => e.id)")
    assert ids == ["an-summary", "an-insights", "an-details", "an-arch"]                   # one summary, one insights section, details and architecture folded away
    assert page.locator(".analytics").count() == 1 and page.title().startswith("Analytics & Intelligence")
    assert page.locator(".an-graphs article").count() == 4 and page.locator(".an-strip > div").count() == 5
    titles = page.eval_on_selector_all(".an-graphs h3", "els => els.map(e => e.innerText)")
    assert len(set(titles)) == 4                                                              # no graph is drawn twice
    assert page.errors == []


@pytest.mark.parametrize("route", ["", "timeline", "labs", "outlook", "statistics", "analytics"])
def test_no_page_is_ever_drawn_twice(page, site, route):
    page.goto(site); page.click("text=Try the sample record"); page.wait_for_selector(".topbar")
    page.goto(f"{site}/#/{route}")
    page.wait_for_selector("main .page")
    page.wait_for_timeout(2500)                                                              # the app redraws the page while the AI text loads
    assert page.locator("main .page").count() == 1


def test_leaving_and_coming_back_does_not_duplicate_the_page(page, site):
    open_page(page, site)
    page.goto(f"{site}/#/labs"); page.wait_for_selector(".labgrid")
    page.goto(f"{site}/#/analytics"); page.wait_for_selector("#an-insights")
    assert page.locator(".analytics").count() == 1 and page.locator("#an-summary").count() == 1


def test_the_two_models_each_have_their_own_clearly_named_part_and_say_when_they_are_off(page, site):   # both models are off on the test site
    open_page(page, site)
    assert "NVIDIA Nemotron" in page.inner_text("#an-summary") and "Google MedGemma" in page.inner_text("#an-insights")
    assert page.locator("#an-summary .an-btn").is_disabled() and "switched off" in page.inner_text("#an-summary").lower()
    assert "not connected" in page.inner_text("#an-insights").lower() and page.locator("#an-insights > .an-actions .an-btn").is_disabled()
    assert page.locator(".an-explain").count() == 4                                           # each graph has a place for Nemotron's explanation
    assert page.locator("#an-compare").count() == 0                                           # the comparison is only offered when it is switched on


def test_the_statistics_are_in_one_folded_place_with_real_values(page, site):
    open_page(page, site)
    assert page.locator("#an-details > details").count() == 1 and page.locator("#an-details details.an-block").count() >= 9
    page.locator("#an-details > details > summary").click()
    page.locator("#an-details details.an-block >> nth=1").locator("summary").click()
    row = page.locator("#an-details .an-table tbody tr").first.inner_text()
    assert row.strip() and "NaN" not in row
    text = page.inner_text(".analytics")
    assert "NaN" not in text and "undefined" not in text


def test_the_question_box_gives_the_fixed_reply_to_unsafe_questions_and_labels_the_rest(page, site):
    open_page(page, site)
    page.locator("#an-insights >> text=Ask a medical question").click()
    page.fill(".an-ask", "I have chest pain"); page.click(".an-askbox .an-btn")
    page.wait_for_selector(".an-askbox >> text=emergency number")
    page.fill(".an-ask", "Should I stop my medicine?"); page.click(".an-askbox .an-btn")
    page.wait_for_selector(".an-askbox >> text=can’t advise on medicines")
    page.fill(".an-ask", "How is my blood pressure?"); page.click(".an-askbox .an-btn")
    page.wait_for_selector(".an-askbox >> text=not approved")                               # this record is not approved for an external model, so nothing was sent
    assert page.errors == []


def test_the_architecture_opens_and_lists_every_part_with_its_state(page, site):
    open_page(page, site)
    page.locator("#an-arch > details > summary").click()
    assert page.locator("#an-arch .an-node").count() == 10
    page.locator("#an-arch .an-node > summary >> text=Google MedGemma").first.click()
    inner = page.inner_text("#an-arch")
    assert "off" in inner.lower() and "src/prana/ai/medgemma.py" in inner and page.locator("#an-arch .an-bad").count() == 0


def test_the_page_fits_a_phone_without_sideways_scrolling(browser, site):
    ctx = browser.new_context(viewport={"width": 390, "height": 800}, is_mobile=True)
    pg = ctx.new_page()
    pg.goto(site); pg.click("text=Try the sample record"); pg.wait_for_selector(".topbar")
    pg.goto(f"{site}/#/analytics"); pg.wait_for_selector("#an-insights", timeout=15000)
    pg.evaluate("document.querySelectorAll('.analytics details').forEach(d => d.open = true)")
    assert pg.evaluate("document.documentElement.scrollWidth") <= 392
    ctx.close()
