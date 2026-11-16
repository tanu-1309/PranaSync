# ruff: noqa: E702
"""Check that existing pages still look the same after a change: the same page on two running copies of the portal is photographed at desktop and phone
width and compared pixel by pixel.

    python scripts/visual_regression.py --before http://127.0.0.1:8031 --after http://127.0.0.1:8032 [--out DIR] [--tolerance 0.05] [--include-landing]

Run the two copies the same way (same data, and with the AI switched off by PRANA_LLM=0 so AI-written text cannot differ between runs).
Needs `pip install playwright pillow` and a browser (`playwright install chromium`, or Microsoft Edge/Chrome already installed).
Exit code 0 = every page matches within the tolerance (a percentage of changed pixels), 1 = something differs. Differences are saved as images.
The landing page has an animated background, so it is left out unless you ask for it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROUTES = ["", "timeline", "labs", "medications", "outlook", "statistics", "history", "help", "quality", "method", "evidence", "account"]
SIZES = {"desktop": (1440, 900), "mobile": (390, 844)}


def stable_shot(page, url: str, path: Path, tries: int = 4) -> int:
    """Open the page and photograph it. If the portal rendered the page twice at once (a known race in the app's re-render), reload and retry. Returns the number of retries."""
    for attempt in range(tries):
        page.goto(url)
        page.reload(wait_until="load")
        page.wait_for_timeout(3500)
        if page.locator("main .page").count() <= 1 or attempt == tries - 1:
            page.screenshot(path=str(path), full_page=True)
            return attempt
    return tries


def compare(a: Path, b: Path, out: Path, tolerance: float) -> tuple[str, float | None]:
    from PIL import Image, ImageChops
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return f"different size {ia.size} vs {ib.size}", None
    mask = ImageChops.difference(ia, ib).convert("L").point(lambda x: 255 if x > 24 else 0)
    changed = sum(1 for v in mask.getdata() if v) if hasattr(mask, "getdata") else 0
    pct = 100 * changed / (ia.size[0] * ia.size[1])
    if pct > tolerance:
        mask.save(out / f"diff_{a.name}")
    return ("same" if pct <= tolerance else "DIFFERENT"), round(pct, 4)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--out", default="visual_regression_out")
    ap.add_argument("--tolerance", type=float, default=0.05)
    ap.add_argument("--include-landing", action="store_true")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright
    out = Path(args.out)
    (out / "before").mkdir(parents=True, exist_ok=True); (out / "after").mkdir(parents=True, exist_ok=True)
    bad, rows = 0, []
    with sync_playwright() as pw:
        browser = None
        for kw in ({}, {"channel": "msedge"}, {"channel": "chrome"}):
            try:
                browser = pw.chromium.launch(**kw); break
            except Exception:  # noqa: BLE001
                continue
        if browser is None:
            print("No browser available (run: playwright install chromium)"); return 2
        for size, (w, h) in SIZES.items():
            ctxs = {side: browser.new_context(viewport={"width": w, "height": h}) for side in ("before", "after")}
            pages = {side: c.new_page() for side, c in ctxs.items()}
            base = {"before": args.before.rstrip("/"), "after": args.after.rstrip("/")}
            for side, c in ctxs.items():
                if args.include_landing:
                    pages[side].goto(base[side] + "/"); pages[side].wait_for_timeout(2000)
                    pages[side].screenshot(path=str(out / side / f"{size}_landing.png"), full_page=True)
                c.request.post(base[side] + "/api/guest")
            for r in ROUTES:
                name = f"{size}_{r or 'home'}.png"
                retries = {side: stable_shot(pages[side], f"{base[side]}/#/{r}", out / side / name) for side in ("before", "after")}
                verdict, pct = compare(out / "before" / name, out / "after" / name, out, args.tolerance)
                rows.append((name, verdict, pct, sum(retries.values())))
                bad += verdict != "same"
            if args.include_landing:
                name = f"{size}_landing.png"
                verdict, pct = compare(out / "before" / name, out / "after" / name, out, args.tolerance)
                rows.append((name, verdict, pct, 0)); bad += verdict != "same"
            for c in ctxs.values():
                c.close()
        browser.close()
    for name, verdict, pct, retries in rows:
        print(f"{name:32} {verdict:10} {'' if pct is None else f'{pct}% changed':16}{f'  (re-rendered twice, retried {retries}x)' if retries else ''}")
    print(f"\n{len(rows) - bad} of {len(rows)} pages match (tolerance {args.tolerance}% of pixels).")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
