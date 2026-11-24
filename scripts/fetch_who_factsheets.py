# ruff: noqa: E702
"""Save a few World Health Organization fact sheets as text files for the medical knowledge base, and write the manifest that describes them.

    python scripts/fetch_who_factsheets.py --approved-by "Your Name"
    python scripts/ingest_knowledge.py

This is a helper you run yourself. The portal never downloads anything. It reads the public WHO fact-sheet pages, keeps only each page's main text, and records
where it came from (address, the date the page shows, the day you saved it) and who approved it. You are responsible for checking the licence before you use the text.

Licence note, as found: WHO's copyright policy (https://www.who.int/about/policies/publishing/copyright) says publications published by WHO are under CC BY-NC-SA 3.0 IGO
(non-commercial, with attribution, share-alike). These web fact sheets do not state their own licence on the page, so the manifest says that, and the text is for non-commercial
project use only until WHO confirms. The saved text files are git-ignored; the manifest is not.
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
SHEETS = [("hypertension", "who-hypertension", "blood pressure"), ("diabetes", "who-diabetes", "blood sugar and HbA1c"),
          ("cardiovascular-diseases-(cvds)", "who-cardiovascular", "cholesterol and heart disease"), ("obesity-and-overweight", "who-obesity", "weight and BMI"),
          ("physical-activity", "who-physical-activity", "steps and activity"),
          ("healthy-diet", "who-healthy-diet", "diet, salt, sugar and fat"), ("tobacco", "who-tobacco", "smoking"), ("alcohol", "who-alcohol", "alcohol"),
          ("salt-reduction", "who-salt-reduction", "salt and blood pressure"), ("polycystic-ovary-syndrome", "who-pcos", "PCOS"), ("anaemia", "who-anaemia", "anaemia and haemoglobin"),
          ("noncommunicable-diseases", "who-ncd", "chronic disease overview")]
LICENCE = ("WHO publications are CC BY-NC-SA 3.0 IGO under WHO's copyright policy (https://www.who.int/about/policies/publishing/copyright). This web fact sheet does not state its own licence, "
           "so it is used for non-commercial project purposes only until WHO confirms, with attribution to the World Health Organization.")


class Body(HTMLParser):
    """Collects the headings, paragraphs and list items inside the fact sheet's main body."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth, self.inside, self.buf, self.kind, self.parts = 0, False, [], None, []

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class", "") or ""
        if tag in ("div", "article") and not self.inside and "sf-detail-body-wrapper" in cls:
            self.inside, self.depth = True, 1
            return
        if not self.inside:
            return
        if tag in ("div", "article"):
            self.depth += 1
        if tag in ("h2", "h3", "h4", "p", "li") and self.kind is None:      # a paragraph inside a list item stays part of that item
            self.kind, self.buf = tag, []

    def handle_endtag(self, tag):
        if not self.inside:
            return
        if tag in ("h2", "h3", "h4", "p", "li") and self.kind == tag:
            text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
            if text:
                self.parts.append({"h2": "## ", "h3": "### ", "h4": "#### ", "li": "- "}.get(tag, "") + text)
            self.kind = None
        if tag in ("div", "article"):
            self.depth -= 1
            if self.depth <= 0:
                self.inside = False

    def handle_data(self, data):
        if self.inside and self.kind:
            self.buf.append(data)


def fetch(slug: str) -> tuple[str, str, str, str]:
    url = f"https://www.who.int/news-room/fact-sheets/detail/{slug}"
    html = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "ignore")
    title = re.sub(r"\s+", " ", re.findall(r"<h1[^>]*>(.*?)</h1>", html, flags=re.S)[0]).strip()
    head = html[:html.find("sf-detail-body-wrapper")]
    head_text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", head, flags=re.S)))
    shown = re.findall(r"(\d{1,2} [A-Z][a-z]+ 20\d\d)", head_text[-600:])[-1]     # the date printed under the title, just above the text
    parser = Body(); parser.feed(html)
    # paragraphs repeat when a list item holds a paragraph: drop exact repeats that follow each other
    parts = [p for i, p in enumerate(parser.parts) if i == 0 or p != parser.parts[i - 1]]
    return url, title, datetime.strptime(shown, "%d %B %Y").date().isoformat(), "\n\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--approved-by", required=True, help="the person who approves using these documents")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    entries = []
    for slug, sid, topic in SHEETS:
        try:
            url, title, published, body = fetch(slug)
        except Exception as e:      # a page that moved or changed layout is skipped, not fatal
            print(f"{sid}: could not be read ({type(e).__name__}), skipped"); continue
        words = len(body.split())
        if words < 150:
            print(f"{sid}: only {words} words found, skipped"); continue
        (OUT / f"{sid}.md").write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
        entries.append({"source_id": sid, "file": f"{sid}.md", "title": f"{title} (WHO fact sheet)", "publisher": "World Health Organization", "source_type": "government", "url": url,
                        "published": published, "version": f"fact sheet dated {published}", "license": LICENCE, "retrieved_on": date.today().isoformat(), "approved_by": a.approved_by})
        print(f"{sid}: saved {words} words (shown date {published}; covers {topic})")
    old = yaml.safe_load((OUT / "manifest.yaml").read_text(encoding="utf-8")) if (OUT / "manifest.yaml").exists() else {}
    keep = [e for e in (old or {}).get("sources", []) if not str(e.get("source_id", "")).startswith("who-")]      # sources added by other scripts stay
    (OUT / "manifest.yaml").write_text("# Written by scripts/fetch_who_factsheets.py and scripts/fetch_medical_sources.py. Clinician review of these sources is still to do.\n"
                                       + yaml.safe_dump({"sources": entries + keep}, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"manifest written with {len(entries)} sources: {OUT / 'manifest.yaml'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
