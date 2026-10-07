"""Load and clean one patient workbook (owner: Sneha).

Input : one Prana Chain .xlsx (11 sheets).
Output: a `PatientRecord` with tidy, typed DataFrames + a data-quality log.

Cleaning steps (every step is counted in `quality` so we can report it):
  1. rename columns via config/column_map.yaml
  2. parse dates (Excel serial numbers OR real dates)
  3. coerce numbers, blank / "N/A" -> missing
  4. remove impossible values (plausibility limits in column_map.yaml)
  5. drop duplicate days (keep the mean of duplicate readings)
  6. normalise lab names and units (glucose mmol/L -> mg/dL)
  7. keep everything inside the 12-month data window
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from prana.config import column_map

EXCEL_EPOCH = datetime(1899, 12, 30)
DAILY_SHEETS = ("vitals", "wearable")


@dataclass
class PatientRecord:
    patient_id: str
    profile: dict
    sheets: dict[str, pd.DataFrame]
    quality: dict = field(default_factory=dict)
    window: tuple[pd.Timestamp, pd.Timestamp] | None = None

    @property
    def sex(self) -> str:
        return str(self.profile.get("Sex", "")).strip().lower()

    def get(self, key: str) -> pd.DataFrame:
        return self.sheets.get(key, pd.DataFrame())


def to_date(s: pd.Series) -> pd.Series:
    """Excel serials (45901) and real dates/strings -> pandas Timestamps."""
    num = pd.to_numeric(s, errors="coerce")
    out = pd.to_datetime(s, errors="coerce")
    serial_mask = num.notna() & (num > 20000) & (num < 80000)
    out[serial_mask] = [EXCEL_EPOCH + timedelta(days=float(v)) for v in num[serial_mask]]
    return pd.to_datetime(out).dt.normalize()


def _parse_profile(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    df = df.iloc[:, :2]
    df.columns = ["field", "value"]
    return {str(k).strip(): v for k, v in zip(df["field"], df["value"]) if pd.notna(k)}


def _window(profile: dict) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    m = re.findall(r"\d{4}-\d{2}-\d{2}", str(profile.get("Data Window", "")))
    return (pd.Timestamp(m[0]), pd.Timestamp(m[1])) if len(m) == 2 else None


def load_workbook(path: str | Path) -> PatientRecord:
    path = Path(path)
    cmap = column_map()
    xl = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    q: dict = {"file": path.name, "sheets_found": len(xl), "missing_sheets": []}

    profile = _parse_profile(xl.get(cmap["sheets"]["profile"], pd.DataFrame()))
    pid = str(profile.get("Patient ID", path.stem))
    window = _window(profile)

    sheets: dict[str, pd.DataFrame] = {}
    for key, sheet_name in cmap["sheets"].items():
        if key == "profile":
            continue
        if sheet_name not in xl:
            q["missing_sheets"].append(sheet_name)
            sheets[key] = pd.DataFrame()
            continue
        df = xl[sheet_name].copy()
        df.columns = [str(c).strip() for c in df.columns]
        df = df.rename(columns=cmap["columns"].get(key, {}))
        df = df.dropna(how="all")
        for col in [c for c in df.columns if c in ("date", "start_date", "end_date")]:
            df[col] = to_date(df[col])
        sheets[key] = df

    _clean_daily(sheets, cmap, q)
    _clean_labs(sheets, cmap, q)
    _clean_women(sheets, cmap, q)

    if window is not None:
        lo, hi = window
        for key in DAILY_SHEETS + ("labs", "women", "habits", "symptoms"):
            df = sheets.get(key, pd.DataFrame())
            if not df.empty and "date" in df:
                before = len(df)
                sheets[key] = df[(df["date"] >= lo) & (df["date"] <= hi)].reset_index(drop=True)
                q.setdefault("outside_window", 0)
                q["outside_window"] += before - len(sheets[key])
    else:
        dates = sheets["vitals"]["date"] if not sheets["vitals"].empty else pd.Series(dtype="datetime64[ns]")
        window = (dates.min(), dates.max()) if len(dates) else None

    return PatientRecord(pid, profile, sheets, q, window)


def _clean_daily(sheets, cmap, q):
    limits = cmap.get("plausible", {})
    for key in DAILY_SHEETS:
        df = sheets.get(key, pd.DataFrame())
        if df.empty:
            continue
        value_cols = [c for c in df.columns if c != "date"]
        for c in value_cols:
            df[c] = pd.to_numeric(df[c].replace({"N/A": np.nan, "NA": np.nan, "": np.nan, "-": np.nan}), errors="coerce")
        q[f"{key}_blank_cells"] = int(df[value_cols].isna().sum().sum())
        impossible = 0
        for c in value_cols:
            if c in limits:
                lo, hi = limits[c]
                bad = df[c].notna() & ((df[c] < lo) | (df[c] > hi))
                impossible += int(bad.sum())
                df.loc[bad, c] = np.nan
        q[f"{key}_impossible_values"] = impossible
        df = df.dropna(subset=["date"])
        q[f"{key}_duplicate_days"] = int(df["date"].duplicated().sum())
        df = df.groupby("date", as_index=False)[value_cols].mean()
        q[f"{key}_days"] = int(len(df))
        sheets[key] = df


def _clean_labs(sheets, cmap, q):
    df = sheets.get("labs", pd.DataFrame())
    if df.empty:
        q["lab_rows"] = 0
        return
    lab_names = {k.lower(): v for k, v in cmap.get("labs", {}).items()}
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["test_key"] = df["test"].astype(str).str.strip().str.lower().map(
        lambda t: lab_names.get(t, re.sub(r"[^a-z0-9]+", "_", t).strip("_")))
    unit = df["unit"].astype(str).str.lower()
    fix = (df["test_key"] == "fasting_glucose") & unit.str.contains("mmol")
    df.loc[fix, "value"] = (df.loc[fix, "value"] * 18.0).round(1)
    df.loc[fix, "unit"] = "mg/dL"
    q["lab_unit_conversions"] = int(fix.sum())
    df = df.dropna(subset=["date", "value"])
    q["lab_duplicates"] = int(df.duplicated(["date", "test_key"]).sum())
    df = df.drop_duplicates(["date", "test_key"]).sort_values(["test_key", "date"]).reset_index(drop=True)
    # derived lab: LH/FSH ratio (used in the PCOS scenario)
    lh = df[df.test_key == "lh"].set_index("date")["value"]
    fsh = df[df.test_key == "fsh"].set_index("date")["value"]
    both = lh.index.intersection(fsh.index)
    if len(both):
        ratio = pd.DataFrame({"date": both, "test": "LH/FSH ratio", "value": (lh[both] / fsh[both]).round(2).values,
                              "unit": "ratio", "ref_range": "<2", "test_key": "lh_fsh_ratio"})
        df = pd.concat([df, ratio], ignore_index=True)
    q["lab_rows"] = int(len(df))
    sheets["labs"] = df


def _clean_women(sheets, cmap, q):
    df = sheets.get("women", pd.DataFrame())
    if df.empty or "date" not in df:
        q["cycles"] = 0
        return
    df["cycle_length"] = pd.to_numeric(df["cycle_length"], errors="coerce")
    lo, hi = cmap["plausible"]["cycle_length"]
    df.loc[(df["cycle_length"] < lo) | (df["cycle_length"] > hi), "cycle_length"] = np.nan
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    q["cycles"] = int(len(df))
    sheets["women"] = df


def list_workbooks(folder: str | Path) -> list[Path]:
    return sorted(p for p in Path(folder).rglob("*.xlsx") if not p.name.startswith("~$"))
