"""Reference-value layer: the bands, the lab's own ranges, and how it relates to change detection."""
import importlib.util
from pathlib import Path

import pytest

from prana.analysis import reference as ref
from prana.insight.pipeline import analyze_workbook


@pytest.mark.parametrize("sbp,dbp,flag,label", [
    (112, 72, "within", "Typical"), (124, 76, "watch", "Slightly above typical"), (134, 78, "watch", "Above typical"),
    (118, 86, "watch", "Above typical"), (146, 82, "outside", "Well above typical"), (122, 92, "outside", "Well above typical"),
    (88, 70, "watch", "Below typical"),
])
def test_blood_pressure_categories_use_the_higher_reading(sbp, dbp, flag, label):
    c = ref.bp_category(sbp, dbp)
    assert (c["flag"], c["label"]) == (flag, label)


@pytest.mark.parametrize("text,expected", [("4.0–5.6", (4.0, 5.6)), ("7-56", (7.0, 56.0)), ("<5.7", (None, 5.7)), (">40", (40.0, None)),
                                           ("1,000–2,000", (1000.0, 2000.0)), ("n/a", None), (None, None)])
def test_lab_range_parsing(text, expected):
    assert ref.parse_ref_range(text) == expected


def _band_groups(cfg):
    for key, c in {**cfg["daily"], **cfg["labs"]}.items():
        if "bands" in c:
            yield key, c["bands"]
        for sex, g in c.get("by_sex", {}).items():
            yield f"{key}/{sex}", g["bands"]


def test_bands_are_half_open_and_cover_every_value():
    groups = list(_band_groups(ref.reference_config()))
    assert len(groups) >= 12
    for key, bands in groups:
        assert all(b["flag"] in ref.FLAG_RANK for b in bands), key
        assert bands[0]["lo"] is None and bands[-1]["hi"] is None, f"{key}: open ends required"
        for prev, nxt in zip(bands, bands[1:]):
            assert prev["hi"] == nxt["lo"], f"{key}: gap or overlap between bands"


def test_hba1c_bands_and_unit_guard():
    b = ref.reference_config()["labs"]["hba1c"]["bands"]
    assert [ref.band_for(v, b)["label"] for v in (5.2, 5.7, 6.4, 6.5)] == ["Typical", "Above typical", "Above typical", "Well above typical"]


def test_relation_separates_the_two_questions():
    assert ref._relation("within", "stable") == "within"
    assert ref._relation("outside", "stable") == "steady_outside"   # the case a change-only view would miss
    assert ref._relation("watch", None) == "steady_outside"
    assert ref._relation("outside", "changed") == "changed_outside"
    assert ref._relation("within", "changed") == "changed_within"


def test_pipeline_attaches_reference_without_touching_detection(workbooks):
    result, rec, _ = analyze_workbook(workbooks["t2d"])
    r = result["reference"]
    assert r["items"] and set(r["counts"]) == {"within", "watch", "outside"}
    assert sum(r["counts"].values()) == len(r["items"])
    for it in r["items"]:
        assert it["flag"] in ref.FLAG_RANK and it["relation"] and it["reference_text"] and it["source"]
    # the sources are named, and no category is worded as a condition
    text = " ".join(str(it["category"]).lower() for it in r["items"])
    for banned in ("diabetes", "hypertension", "diagnos"):
        assert banned not in text


def test_personal_only_signals_get_no_population_reference(workbooks):
    result, _, _ = analyze_workbook(workbooks["t2d"])
    keys = {it["key"] for it in result["reference"]["items"]}
    assert not keys & set(result["reference"]["personal_only"])


def test_password_generator_is_random_and_unambiguous():
    spec = importlib.util.spec_from_file_location("create_users", Path(__file__).resolve().parents[1] / "scripts" / "create_users.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pws = {mod.new_password() for _ in range(2000)}
    assert len(pws) == 2000                                   # no repeats
    for p in list(pws)[:200]:
        assert len(p) == 14 and p.count("-") == 2
        assert not set(p) & set("0O1lI")                      # no look-alikes
