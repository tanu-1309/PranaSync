"""Analysis tests (Sindhu)."""
import numpy as np
import pandas as pd

from prana.analysis.baseline import assess_daily, assess_lab, mann_kendall
from prana.analysis.patterns import detect_all
from prana.config import scenarios_config
from prana.data.loader import load_workbook

D = scenarios_config()["defaults"]
IDX = pd.date_range("2025-09-01", periods=365, freq="D")
rng = np.random.default_rng(0)


def test_flat_signal_is_stable():
    s = pd.Series(8000 + rng.normal(0, 1200, 365), index=IDX)
    assert assess_daily(s, "down", D, "15%")["status"] == "stable"


def test_step_change_is_detected_with_onset():
    v = 8000 + rng.normal(0, 1200, 365)
    v[180:] -= 3000
    a = assess_daily(pd.Series(v, index=IDX), "down", D, "15%")
    assert a["status"] == "changed"
    assert abs((pd.Timestamp(a["onset_date"]) - IDX[180]).days) <= 21


def test_recovered_dip_is_not_reported():
    v = 8000 + rng.normal(0, 1200, 365)
    v[150:180] -= 4000
    assert assess_daily(pd.Series(v, index=IDX), "down", D, "15%")["status"] != "changed"


def test_wrong_direction_is_not_a_concern():
    v = 8000 + rng.normal(0, 1200, 365)
    v[180:] += 3000
    assert assess_daily(pd.Series(v, index=IDX), "down", D, "15%")["status"] == "improving"


def test_low_coverage_is_insufficient():
    v = pd.Series(8000.0, index=IDX)
    v[::2] = np.nan
    v[1::4] = np.nan
    assert assess_daily(v, "down", D, "15%")["status"] == "insufficient_data"


def test_mann_kendall_sign():
    assert mann_kendall(np.arange(20.0))[0] > 0
    assert mann_kendall(np.arange(20.0)[::-1])[1] < 0.05


def test_lab_change_needs_min_delta():
    s = pd.Series([5.8, 5.9, 6.2, 6.3], index=pd.to_datetime(["2025-09-10", "2025-12-10", "2026-03-10", "2026-06-10"]))
    assert assess_lab(s, "up", 0.3)["status"] == "changed"
    assert assess_lab(s, "up", 0.6)["status"] == "stable"


def _surfaced(path):
    return {r["scenario"]: r for r in detect_all(load_workbook(path))}


def test_planted_patterns_surface(workbooks):
    assert _surfaced(workbooks["t2d"])["t2d"]["surfaced"]
    assert _surfaced(workbooks["htn"])["htn"]["surfaced"]
    assert _surfaced(workbooks["pcos"])["pcos"]["surfaced"]


def test_no_pattern_for_control_and_single_signal(workbooks):
    for name in ("control", "single_signal"):
        assert not any(r["surfaced"] for r in _surfaced(workbooks[name]).values()), name


def test_pcos_not_applicable_for_male(workbooks):
    assert _surfaced(workbooks["control"])["pcos"]["applicable"] is False
