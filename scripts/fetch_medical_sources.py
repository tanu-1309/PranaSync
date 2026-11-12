# ruff: noqa: E702
"""Save public medical reference pages (MedlinePlus, CDC, NIH) as text files for the medical knowledge base, and add them to the manifest.

    python scripts/fetch_medical_sources.py --approved-by "Your Name"
    python scripts/ingest_knowledge.py

A helper you run yourself: the portal never downloads anything. It covers what the five original WHO sheets did not: cholesterol (LDL, HDL, triglycerides), the HbA1c and
glucose tests, thyroid, vitamin D, PCOS, high blood pressure and type 2 diabetes in plain language. It keeps only each page's main text, records the address, the date the page shows
(or the day it was saved) and who approved it, and merges with the existing manifest (WHO entries are left alone). A page that moved or changed layout is skipped, not fatal.

Licence note, as found: MedlinePlus (US National Library of Medicine) and NIH/CDC pages are US government works; MedlinePlus states its information is free of copyright restrictions
unless a page says otherwise. Check each page's notice yourself before using the text, and attribute the publisher. These are patient-education pages, not clinical guidelines, so
they explain what a topic or test is. They do not give the detailed thresholds a guideline would. No clinician has reviewed them.
"""
import argparse
import re
import sys
import urllib.request
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "knowledge"
UA = {"User-Agent": "Mozilla/5.0 (PranaSync student project; non-commercial research use)"}
PAGES = [  # (source_id, url, publisher, what it covers)
    ("medlineplus-cholesterol", "https://medlineplus.gov/cholesterol.html", "MedlinePlus (US National Library of Medicine)", "cholesterol, LDL, HDL"),
    ("medlineplus-cholesterol-levels", "https://medlineplus.gov/lab-tests/cholesterol-levels/", "MedlinePlus (US National Library of Medicine)", "cholesterol test results"),
    ("medlineplus-triglycerides", "https://medlineplus.gov/lab-tests/triglycerides-test/", "MedlinePlus (US National Library of Medicine)", "triglycerides test"),
    ("medlineplus-hba1c", "https://medlineplus.gov/lab-tests/hemoglobin-a1c-hba1c-test/", "MedlinePlus (US National Library of Medicine)", "HbA1c test"),
    ("medlineplus-blood-glucose", "https://medlineplus.gov/lab-tests/blood-glucose-test/", "MedlinePlus (US National Library of Medicine)", "fasting glucose test"),
    ("medlineplus-high-blood-pressure", "https://medlineplus.gov/highbloodpressure.html", "MedlinePlus (US National Library of Medicine)", "high blood pressure"),
    ("medlineplus-type2-diabetes", "https://medlineplus.gov/diabetestype2.html", "MedlinePlus (US National Library of Medicine)", "type 2 diabetes"),
    ("medlineplus-prediabetes", "https://medlineplus.gov/prediabetes.html", "MedlinePlus (US National Library of Medicine)", "prediabetes"),
    ("medlineplus-pcos", "https://medlineplus.gov/polycysticovarysyndrome.html", "MedlinePlus (US National Library of Medicine)", "PCOS"),
    ("medlineplus-thyroid-tests", "https://medlineplus.gov/lab-tests/tsh-thyroid-stimulating-hormone-test/", "MedlinePlus (US National Library of Medicine)", "TSH test"),
    ("medlineplus-vitamin-d", "https://medlineplus.gov/lab-tests/vitamin-d-test/", "MedlinePlus (US National Library of Medicine)", "vitamin D test"),
    ("medlineplus-kidney-tests", "https://medlineplus.gov/lab-tests/glomerular-filtration-rate-gfr-test/", "MedlinePlus (US National Library of Medicine)", "eGFR and kidney function"),
    ("cdc-high-blood-pressure", "https://www.cdc.gov/high-blood-pressure/about/index.html", "US Centers for Disease Control and Prevention", "high blood pressure"),
    ("cdc-cholesterol", "https://www.cdc.gov/cholesterol/about/index.html", "US Centers for Disease Control and Prevention", "cholesterol"),
    ("cdc-diabetes", "https://www.cdc.gov/diabetes/about/index.html", "US Centers for Disease Control and Prevention", "diabetes"),
    ("nih-vitamin-d", "https://ods.od.nih.gov/factsheets/VitaminD-Consumer/", "NIH Office of Dietary Supplements", "vitamin D"),
]
SKIP = {"nav", "header", "footer", "aside", "script", "style", "form", "noscript", "button", "svg"}
MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
LICENCE = ("US government work. MedlinePlus states its information is free of copyright restrictions unless a page says otherwise; NIH and CDC pages are US government works. "
           "Used for non-commercial project purposes with attribution to the publisher. Check the page's own notice before reuse.")


class Main(HTMLParser):
    """Collects headings, paragraphs and list items from the page's main region, skipping navigation, headers, footers and forms."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip, self.main, self.kind, self.buf, self.parts = 0, 0, None, [], []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
        if tag in ("main", "article"):
            self.main += 1
        if self.skip or not self.main:
            return
        if tag in ("h2", "h3", "h4", "p", "li") and self.kind is None:
            self.kind, self.buf = tag, []

    def handle_endtag(self, tag):
        if tag in SKIP and self.skip:
            self.skip -= 1
            return
        if self.skip or not self.main:
            return
        if tag in ("h2", "h3", "h4", "p", "li") and self.kind == tag:
            text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
            if text and len(text) > 2:
                self.parts.append({"h2": "## ", "h3": "### ", "h4": "#### ", "li": "- "}.get(tag, "") + text)
            self.kind = None
        if tag in ("main", "article"):
            self.main = max(0, self.main - 1)

    def handle_data(self, data):
        if self.kind and not self.skip and self.main:
            self.buf.append(data)


def fetch(url: str) -> tuple[str, str, str]:
    html = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "ignore")
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", (re.findall(r"<h1[^>]*>(.*?)</h1>", html, flags=re.S) or ["Untitled"])[0])).strip()
    shown = re.findall(rf"(?:[Ll]ast [Uu]pdated|[Pp]age last (?:reviewed|updated)|[Uu]pdated|[Ll]ast [Rr]eviewed)[:\s]+({MONTH} \d{{1,2}}, \d{{4}})", re.sub(r"<[^>]+>", " ", html))
    p = Main(); p.feed(html)
    parts = [x for i, x in enumerate(p.parts) if i == 0 or x != p.parts[i - 1]]
    d = None
    if shown:
        try:
            d = datetime.strptime(shown[-1], "%B %d, %Y").date().isoformat()
        except ValueError:
            d = None
    return title, d or "", "\n\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--approved-by", required=True, help="the person who approves using these documents")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    new = []
    for sid, url, publisher, topic in PAGES:
        try:
            title, shown, body = fetch(url)
        except Exception as e:
            print(f"{sid}: could not be read ({type(e).__name__}), skipped"); continue
        words = len(body.split())
        if words < 150:
            print(f"{sid}: only {words} words found, skipped"); continue
        (OUT / f"{sid}.md").write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
        published = shown or date.today().isoformat()
        new.append({"source_id": sid, "file": f"{sid}.md", "title": f"{title} ({publisher.split(' (')[0]})", "publisher": publisher, "source_type": "government", "url": url, "published": published,
                    "version": f"page dated {published}" if shown else f"page as retrieved on {date.today().isoformat()}", "license": LICENCE, "retrieved_on": date.today().isoformat(), "approved_by": a.approved_by})
        print(f"{sid}: saved {words} words (covers {topic})")
    path = OUT / "manifest.yaml"
    old = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    ids = {e["source_id"] for e in new}
    keep = [e for e in (old or {}).get("sources", []) if e.get("source_id") not in ids]
    path.write_text("# Written by scripts/fetch_who_factsheets.py and scripts/fetch_medical_sources.py. Clinician review of these sources is still to do.\n"
                    + yaml.safe_dump({"sources": keep + new}, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"manifest now lists {len(keep) + len(new)} sources ({len(new)} added or refreshed): {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
