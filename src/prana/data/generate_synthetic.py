"""Synthetic workbook generator (owner: Sneha).

Writes patient workbooks with EXACTLY the same 11 sheets and column names as
the Prana Chain dataset (checked against PC0001.xlsx), but with patterns we
planted on purpose. Because we know what we planted, these files are our
ground truth for validation (see scripts/validate.py).

Archetypes
----------
t2d / htn / pcos   : multi-signal drift + matching past finding in history
control            : stable year, normal history
noisy_control      : stable but noisy, with a 2-week dip that recovers
context_only       : past finding in history but signals stay stable
drift_no_context   : t2d- or htn-like drift but nothing in the history
single_signal      : only systolic BP rises (a threshold alert would fire,
                     a multi-signal pattern should NOT)

Each workbook also gets realistic data-quality problems: duplicate days,
blank cells, impossible values, glucose in mmol/L instead of mg/dL.

Usage:  python -m prana.data.generate_synthetic --n 120 --out data/synthetic
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

START = date(2025, 9, 1)
DAYS = 365
EXCEL_EPOCH = date(1899, 12, 30)

MIX = {  # archetype: count per 120 patients
    "t2d": 18, "htn": 18, "pcos": 14, "control": 24, "noisy_control": 14,
    "context_only": 12, "drift_no_context": 10, "single_signal": 10,
}

HISTORY_FINDING = {
    "t2d": ("Clinical finding", "Borderline glycemic markers", "Monitoring", "Repeat testing planned"),
    "htn": ("Clinical finding", "Elevated blood pressure readings", "Monitoring", "Home BP monitoring advised"),
    "pcos": ("Clinical finding", "Irregular menstrual cycles", "Monitoring", "Cycle tracking advised"),
}


def serial(d: date) -> int:
    """Excel serial number, as used in the real workbooks (45901 = 2025-09-01)."""
    return (d - EXCEL_EPOCH).days


def ramp(onset: int, full: int, n: int = DAYS) -> np.ndarray:
    """0 before onset, linear rise to 1 at `full`, then 1."""
    x = np.arange(n, dtype=float)
    return np.clip((x - onset) / max(full - onset, 1), 0, 1)


def make_patient(pid: str, archetype: str, rng: np.random.Generator, missing: str | None = None,
                 effect: float = 1.0):
    """effect scales every planted change (1.0 = clear pattern, 0.4 = subtle)."""
    sub = None
    if archetype in ("drift_no_context", "context_only"):
        sub = rng.choice(["t2d", "htn"] if archetype == "drift_no_context" else ["t2d", "htn", "pcos"])
    female = archetype == "pcos" or (sub == "pcos") or rng.random() < 0.5
    age = int(rng.integers(19, 38)) if (archetype == "pcos" or sub == "pcos") else int(rng.integers(28, 72))
    height = int(rng.normal(163 if female else 176, 6))
    weight0 = float(rng.normal(78 if female else 88, 10))

    drift = archetype if archetype in ("t2d", "htn", "pcos") else (sub if archetype == "drift_no_context" else None)
    onset = int(rng.integers(110, 200))
    full = onset + int(rng.integers(60, 120))
    r = ramp(onset, full)
    noise = 1.6 if archetype == "noisy_control" else 1.0
    days = [START + timedelta(days=i) for i in range(DAYS)]

    # ---------------- baselines + planted drift -----------------
    sbp0, dbp0 = rng.normal(124, 6), rng.normal(79, 4)
    rhr0, hrv0 = rng.normal(68, 5), rng.normal(42, 8)
    steps0, sleep0 = rng.normal(8200, 1200), rng.normal(7.0, 0.4)
    act0, sed0 = rng.normal(45, 8), rng.normal(9.5, 1.0)

    d_sbp = d_dbp = d_rhr = d_hrv = d_steps = d_sleep = d_act = d_sed = d_wt = 0.0
    if drift == "t2d":
        d_steps = -rng.uniform(0.28, 0.40) * steps0
        d_act = -rng.uniform(0.30, 0.45) * act0
        d_sed = rng.uniform(1.5, 2.5)
        d_wt = rng.uniform(3.5, 6.0)
        d_sleep = -rng.uniform(0.8, 1.2)
    elif drift == "htn":
        d_sbp, d_dbp = rng.uniform(11, 18), rng.uniform(7, 11)
        d_rhr, d_hrv = rng.uniform(6, 10), -rng.uniform(0.25, 0.35) * hrv0
        d_sleep = -rng.uniform(0.8, 1.2)
    elif drift == "pcos":
        d_wt, d_sleep = rng.uniform(3.5, 5.5), -rng.uniform(0.8, 1.2)
    if archetype == "single_signal":
        d_sbp = rng.uniform(14, 20)
    else:
        d_sbp, d_dbp, d_rhr, d_hrv = d_sbp * effect, d_dbp * effect, d_rhr * effect, d_hrv * effect
        d_steps, d_sleep, d_act, d_sed, d_wt = d_steps * effect, d_sleep * effect, d_act * effect, d_sed * effect, d_wt * effect

    wt_walk = np.cumsum(rng.normal(0, 0.03, DAYS))  # natural slow wander (<~1 kg)
    sbp = sbp0 + d_sbp * r + rng.normal(0, 5.5 * noise, DAYS)
    dbp = dbp0 + d_dbp * r + rng.normal(0, 3.8 * noise, DAYS)
    rhr = rhr0 + d_rhr * r + rng.normal(0, 4.0 * noise, DAYS)
    wt = weight0 + d_wt * r + wt_walk + rng.normal(0, 0.3 * noise, DAYS)
    steps = steps0 + d_steps * r + rng.normal(0, 1300 * noise, DAYS)
    sleep = sleep0 + d_sleep * r + rng.normal(0, 0.75 * noise, DAYS)
    act = act0 + d_act * r + rng.normal(0, 10 * noise, DAYS)
    sed = sed0 + d_sed * r + rng.normal(0, 1.0 * noise, DAYS)
    hrv = hrv0 + d_hrv * r + rng.normal(0, 6 * noise, DAYS)
    weekend = np.array([d.weekday() >= 5 for d in days])
    steps = steps + np.where(weekend, 900, 0)

    if archetype == "noisy_control":  # a 2-week illness/vacation dip that recovers
        s = int(rng.integers(120, 300))
        steps[s:s + 14] *= 0.55
        sleep[s:s + 14] -= 1.0
        rhr[s:s + 14] += 6

    vitals = pd.DataFrame({
        "Date": [serial(d) for d in days],
        "Systolic BP": np.round(sbp).astype(int), "Diastolic BP": np.round(dbp).astype(int),
        "Resting HR": np.round(rhr).astype(int), "Weight kg": np.round(wt, 1),
        "BMI": np.round(wt / (height / 100) ** 2, 1),
        "SpO2 %": np.round(rng.normal(97.4, 0.5, DAYS).clip(92, 100), 1),
        "Temp C": np.round(rng.normal(36.7, 0.15, DAYS), 1),
        "Respiratory Rate": np.round(rng.normal(14, 1.5, DAYS), 1),
    })
    wearable = pd.DataFrame({
        "Date": [serial(d) for d in days],
        "Steps": np.round(steps.clip(300)).astype(int), "Sleep Hours": np.round(sleep.clip(2.5, 11), 1),
        "Active Minutes": np.round(act.clip(0)).astype(int), "Resting HR": np.round(rhr + rng.normal(0, 1, DAYS)).astype(int),
        "HRV ms": np.round(hrv.clip(8)).astype(int), "Calories kcal": np.round(rng.normal(2050, 180, DAYS)).astype(int),
        "Sedentary Hours": np.round(sed.clip(2, 18), 1), "Stress Score 1-10": np.round(rng.normal(5, 1, DAYS).clip(1, 10), 1),
    })

    # ---------------- labs (5 draws, ~quarterly) -----------------
    lab_days = [9, 100, 190, 282, 353]
    a1c0 = rng.normal(5.9, 0.12) if (drift == "t2d" or sub == "t2d") and archetype != "drift_no_context" else rng.normal(5.3, 0.15)
    glu0 = 104 + rng.normal(0, 3) if a1c0 > 5.6 else 90 + rng.normal(0, 4)
    ldl0 = rng.normal(118, 12)
    testo0 = rng.normal(62, 6) if (drift == "pcos" or sub == "pcos") else rng.normal(32, 6)
    labs = []
    for ld in lab_days:
        frac = r[ld]
        dt = serial(START + timedelta(days=ld))
        a1c = a1c0 + (rng.uniform(0.45, 0.7) * effect if drift == "t2d" else 0) * frac + rng.normal(0, 0.12)
        glu = glu0 + (rng.uniform(12, 18) * effect if drift == "t2d" else 0) * frac + rng.normal(0, 4.0)
        ldl = ldl0 + (rng.uniform(15, 22) * effect if drift == "htn" else 0) * frac + rng.normal(0, 4)
        rows = [("HbA1c", round(a1c, 2), "%", "4.0–5.6"),
                ("Fasting glucose", round(glu, 1), "mg/dL", "70–99"),
                ("LDL cholesterol", round(ldl, 1), "mg/dL", "<100"),
                ("HDL cholesterol", round(rng.normal(55, 6), 1), "mg/dL", ">40"),
                ("Total cholesterol", round(ldl + 75 + rng.normal(0, 5), 1), "mg/dL", "<200"),
                ("Triglycerides", round(rng.normal(140, 15) + (25 * effect * frac if drift == "t2d" else 0), 1), "mg/dL", "<150"),
                ("Creatinine", round(rng.normal(0.85, 0.08), 2), "mg/dL", "0.7–1.3"),
                ("TSH", round(rng.normal(1.6, 0.3), 2), "mIU/L", "0.4–4.0")]
        if female and ld in (9, 190, 353):
            rows += [("Testosterone", round(testo0 + (10 * effect * frac if drift == "pcos" else 0) + rng.normal(0, 3), 1), "ng/dL", "15–70"),
                     ("LH", round(rng.normal(11 if drift == "pcos" or sub == "pcos" else 6, 1), 1), "IU/L", "2–15"),
                     ("FSH", round(rng.normal(5, 0.6), 1), "IU/L", "3–10")]
        labs += [(dt, *row) for row in rows]
    labs = pd.DataFrame(labs, columns=["Date", "Test Name", "Result", "Unit", "Reference Range"])

    # ---------------- history / meds / symptoms / notes -----------------
    hist = [(serial(START - timedelta(days=int(rng.integers(300, 700)))), "Primary care",
             "Annual preventive assessment", "Completed", "Routine history updated")]
    ctx_area = archetype if archetype in ("t2d", "htn", "pcos") else (sub if archetype == "context_only" else None)
    if ctx_area:
        hist.append((serial(START - timedelta(days=int(rng.integers(60, 200)))), *HISTORY_FINDING[ctx_area]))
    history = pd.DataFrame(hist, columns=["Date", "Encounter / Type", "Finding / Event", "Status", "Notes"])

    meds = [("MED-01", "Vitamin D3", "1000 IU", "Once daily", "Oral", serial(START - timedelta(days=200)), None,
             "Active", "Supplement", "Tolerated", "Continued after review")]
    if ctx_area == "t2d" and rng.random() < 0.5:
        meds.append(("MED-02", "Metformin", "500 mg", "Once daily", "Oral", serial(START + timedelta(days=30)), None,
                     "Active", "Metabolic management", "Tolerated", "Started after repeat HbA1c"))
    if ctx_area == "htn" and rng.random() < 0.5:
        meds.append(("MED-02", "Atorvastatin", "10 mg", "Nightly", "Oral", serial(START + timedelta(days=60)), None,
                     "Active", "Lipid management", "Tolerated", "Started after repeat lipid results"))
    medications = pd.DataFrame(meds, columns=["Medication ID", "Medication", "Dose", "Frequency", "Route", "Start Date",
                                              "End Date", "Status", "Indication", "Tolerance / Adverse Effect", "Change Rationale"])

    sym_pool = {"t2d": ["Increased thirst", "Fatigue"], "htn": ["Headache", "Dizziness"], "pcos": ["Acne flare", "Bloating"]}
    syms = []
    for _ in range(int(rng.integers(4, 10))):
        pool = ["Headache", "Fatigue", "Poor sleep", "Muscle soreness"]
        if drift and rng.random() < 0.6:
            pool = sym_pool[drift]
        dday = int(rng.integers(0, DAYS)) if not drift else int(rng.integers(onset, DAYS))
        syms.append((serial(START + timedelta(days=dday)), str(rng.choice(pool)), str(rng.choice(["Mild", "Moderate"])),
                     str(rng.choice(["1 day", "2–3 days", "Intermittent"])), str(rng.choice(["Visit note", "Self-reported"]))))
    symptoms = pd.DataFrame(syms, columns=["Date", "Symptom", "Severity", "Duration", "Source"])

    notes = pd.DataFrame([
        (serial(START + timedelta(days=17)), "Primary care", "Longitudinal health data and recent laboratory results reviewed."),
        (serial(START + timedelta(days=181)), "Follow-up", "Medication, laboratory, vital and lifestyle trends reviewed together."),
    ], columns=["Date", "Encounter", "Clinical Note"])

    adherence = pd.DataFrame([(serial(date(2025 + (m + 8) // 12, (m + 8) % 12 + 1, 1)), "MED-01", int(rng.integers(80, 101)),
                               int(rng.integers(0, 6)), "Refill estimate") for m in range(1, 13)],
                             columns=["Month", "Medication ID", "Estimated Adherence %", "Approx Missed Doses", "Source"])

    weeks = [START + timedelta(days=7 * w) for w in range(52)]
    habits = pd.DataFrame({
        "Week": range(1, 53), "Week Start": [serial(w) for w in weeks],
        "Water L/day": np.round(rng.normal(1.9, 0.3, 52), 1), "Fruit/Veg servings/day": rng.integers(1, 6, 52),
        "Exercise sessions/week": np.clip(np.round(3 - (2 * r[::7][:52] if drift == "t2d" else 0) + rng.normal(0, 0.8, 52)), 0, 7).astype(int),
        "Caffeine cups/day": rng.integers(0, 5, 52), "Alcohol drinks/week": rng.integers(0, 7, 52),
        "Smoking": "Never", "Late meals/week": rng.integers(0, 6, 52),
        "Self-reported stress": rng.choice(["Low", "Moderate", "High"], 52, p=[0.4, 0.45, 0.15]),
    })

    cycles = []
    if female:
        d, c = 0, 1
        while d < DAYS - 20:
            base = rng.normal(29, 1.2)
            if drift == "pcos" and d > onset:
                base = rng.normal(29 + 12 * effect, 5 * max(effect, 0.4))
            L = int(round(base))
            cycles.append((c, serial(START + timedelta(days=d)), L, int(rng.integers(4, 7)),
                           str(rng.choice(["None reported", "Bloating", "Cramps", "Acne"] if drift == "pcos" else ["None reported", "Cramps", "Bloating"])),
                           str(rng.choice(["Mild", "Moderate"]))))
            d += L
            c += 1
    women = pd.DataFrame(cycles, columns=["Cycle", "Start Date", "Cycle Length", "Bleeding Days", "Symptoms", "Severity"])

    # ---------------- realistic data-quality problems -----------------
    for df, cols in ((vitals, ["Systolic BP", "Weight kg", "Resting HR"]), (wearable, ["Steps", "Sleep Hours", "HRV ms"])):
        idx = rng.choice(len(df), int(0.03 * len(df)), replace=False)
        df.loc[idx, rng.choice(cols)] = np.nan
    vitals.loc[int(rng.integers(0, DAYS)), "Weight kg"] = 0.0          # impossible value
    vitals.loc[int(rng.integers(0, DAYS)), "Systolic BP"] = 400        # typo
    dup = vitals.sample(2, random_state=int(rng.integers(1e9)))
    vitals = pd.concat([vitals, dup]).sort_values("Date").reset_index(drop=True)
    g = labs[labs["Test Name"] == "Fasting glucose"].index[0]              # wrong unit
    labs.loc[g, "Result"] = round(labs.loc[g, "Result"] / 18.0, 2)
    labs.loc[g, "Unit"] = "mmol/L"

    # ---------------- missing-data variants -----------------
    expected_missing = []
    if missing == "sparse_wearable":
        idx = rng.choice(DAYS, int(0.42 * DAYS), replace=False)
        wearable.loc[idx, ["Steps", "Sleep Hours", "Active Minutes", "HRV ms", "Sedentary Hours"]] = np.nan
        expected_missing += ["steps", "sleep_hours"]
    elif missing == "no_recent_hba1c":
        labs = labs[~((labs["Test Name"] == "HbA1c") & (labs["Date"] > serial(START + timedelta(days=120))))]
        expected_missing.append("hba1c")
    elif missing == "no_hormone_labs":
        labs = labs[~labs["Test Name"].isin(["Testosterone", "LH", "FSH"])]
        expected_missing += ["testosterone", "lh_fsh_ratio"]
    elif missing == "no_cycle_data":
        women = women.iloc[0:0]
        expected_missing.append("cycle_length")

    profile = pd.DataFrame([
        ("Patient ID", pid), ("Age", age), ("Sex", "Female" if female else "Male"), ("Height (cm)", height),
        ("Blood Group", str(rng.choice(["A+", "B+", "O+", "AB+", "O-"]))), ("Allergies", "No known drug allergies"),
        ("Family History", "Type 2 diabetes (parent)" if archetype == "t2d" and rng.random() < 0.4 else "No major family history documented"),
        ("Data Window", "2025-09-01 to 2026-08-31"),
    ], columns=["Field", "Value"])

    sheets = {"Patient Profile": profile, "Medical History": history, "Medication History": medications,
              "Lab Results": labs, "Vitals Daily": vitals, "Wearable Daily": wearable, "Habits Weekly": habits,
              "Symptoms Timeline": symptoms, "Encounters & Notes": notes, "Medication Adherence": adherence,
              "Women Health": women}

    expected = {"t2d": {"t2d"}, "htn": {"htn"}, "pcos": {"pcos"}}.get(archetype, set())
    if archetype == "drift_no_context":
        expected = {sub}
    truth = {
        "patient_id": pid, "archetype": archetype, "sub_area": sub, "sex": "Female" if female else "Male", "age": age,
        "expected_patterns": sorted(expected),
        "expected_context": sorted({ctx_area} if ctx_area else set()),
        "planted_onset_date": str(START + timedelta(days=onset)) if (drift or archetype == "single_signal") else None,
        "missing_variant": missing, "expected_missing": expected_missing,
    }
    return sheets, truth


def generate(n: int, out: Path, seed: int = 8, effect: float = 1.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out.mkdir(parents=True, exist_ok=True)
    scale = n / sum(MIX.values())
    plan = []
    for arch, k in MIX.items():
        plan += [arch] * max(1, round(k * scale))
    plan = plan[:n]
    truths = []
    for i, arch in enumerate(plan, start=1):
        pid = f"SYN{i:04d}"
        missing = None
        roll = rng.random()
        if arch == "t2d" and roll < 0.3:
            missing = str(rng.choice(["sparse_wearable", "no_recent_hba1c"]))
        elif arch == "pcos" and roll < 0.35:
            missing = str(rng.choice(["no_hormone_labs", "sparse_wearable"]))
        elif arch == "htn" and roll < 0.2:
            missing = "sparse_wearable"
        sheets, truth = make_patient(pid, arch, rng, missing, effect)
        truth["effect"] = effect
        with pd.ExcelWriter(out / f"{pid}.xlsx", engine="openpyxl") as xw:
            for name, df in sheets.items():
                df.to_excel(xw, sheet_name=name, index=False)
        truths.append(truth)
    truth_df = pd.DataFrame(truths)
    truth_df.to_json(out / "ground_truth.json", orient="records", indent=2)
    return truth_df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--out", type=Path, default=Path("data/synthetic"))
    ap.add_argument("--seed", type=int, default=8)
    ap.add_argument("--effect", type=float, default=1.0, help="size of planted changes (1 = clear, 0.4 = subtle)")
    a = ap.parse_args()
    t = generate(a.n, a.out, a.seed, a.effect)
    print(t["archetype"].value_counts().to_string())
    print(f"wrote {len(t)} workbooks + ground_truth.json to {a.out}")


if __name__ == "__main__":
    main()
