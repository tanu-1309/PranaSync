"""Data module tests (Sneha)."""
import pandas as pd

from prana.data.loader import load_workbook, to_date
from prana.data.timeline import build_timeline, daily_series


def test_excel_serial_dates():
    s = to_date(pd.Series([45901, "2025-09-02", None]))
    assert s.iloc[0] == pd.Timestamp("2025-09-01")
    assert s.iloc[1] == pd.Timestamp("2025-09-02")
    assert pd.isna(s.iloc[2])


def test_loads_all_eleven_sheets(workbooks):
    rec = load_workbook(workbooks["control"])
    assert rec.quality["sheets_found"] == 11
    assert rec.quality["missing_sheets"] == []
    assert rec.window == (pd.Timestamp("2025-09-01"), pd.Timestamp("2026-08-31"))


def test_cleaning_fixes_planted_problems(workbooks):
    rec = load_workbook(workbooks["control"])
    q = rec.quality
    assert q["vitals_duplicate_days"] >= 1          # duplicates collapsed
    assert q["vitals_days"] == 365
    assert q["vitals_impossible_values"] >= 2       # weight 0 and SBP 400 removed
    assert rec.get("vitals")["sbp"].max() < 250
    assert q["lab_unit_conversions"] == 1           # glucose mmol/L -> mg/dL
    glu = rec.get("labs").query("test_key == 'fasting_glucose'")["value"]
    assert glu.min() > 50


def test_timeline_has_all_sources(workbooks):
    rec = load_workbook(workbooks["t2d"])
    tl = build_timeline(rec)
    assert {"vitals", "wearable", "lab", "history", "medications", "symptoms"} <= set(tl.source)
    assert tl["date"].is_monotonic_increasing
    assert len(daily_series(rec, "steps")) == 365
