"""Validation against planted ground truth (owner: everyone; maintained by Sindhu).

    python scripts/validate.py --data data/synthetic

Uses the generated workbooks (where we KNOW which pattern was planted) and checks:
  1. pattern detection     precision / recall / specificity per scenario
  2. vs. a threshold alert  the "basic high/low alert" Prana Chain does NOT want
  3. false alarms           on stable, noisy, context-only and single-signal people
  4. timing                 detected pattern start vs. planted onset
  5. context linking        linked to history only when the history really has it
  6. missing data           the system asks for what we removed
  7. robustness             remove the whole wearable sheet -> still works + asks
  8. guardrails             no diagnosis / alarm wording, disclaimer always present
Planned (week 9): fairness by sex/age and a sensitivity analysis (how small a change we can find).
Writes results/validation_report.md, results/metrics.json, results/figures/*.png
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prana.config import RESULTS_DIR, scenarios_config  # noqa: E402
from prana.data.loader import load_workbook  # noqa: E402
from prana.data.timeline import cycle_series, daily_series, lab_series  # noqa: E402
from prana.insight.pipeline import analyze_record  # noqa: E402

SCEN = ["t2d", "htn", "pcos"]
STABLE = ["control", "noisy_control", "context_only", "single_signal"]
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#8a8984"
OUT = RESULTS_DIR


def threshold_alerts(rec) -> dict:
    """The naive 'high/low alert' baseline (any reading over a fixed threshold)."""
    a1c, glu = lab_series(rec, "hba1c"), lab_series(rec, "fasting_glucose")
    sbp, dbp = daily_series(rec, "sbp"), daily_series(rec, "dbp")
    cyc = cycle_series(rec)
    return {"t2d": bool((a1c >= 5.7).any() or (glu >= 100).any()),
            "htn": bool(((sbp >= 140) | (dbp >= 90)).sum() >= 5),
            "pcos": bool(rec.sex == "female" and (cyc > 35).any())}


def prf(df: pd.DataFrame, col: str) -> dict:
    tp = int((df[col] & df.truth).sum())
    fp = int((df[col] & ~df.truth).sum())
    fn = int((~df[col] & df.truth).sum())
    tn = int((~df[col] & ~df.truth).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"TP": tp, "FP": fp, "FN": fn, "TN": tn, "precision": round(p, 3), "recall": round(r, 3),
            "specificity": round(tn / (tn + fp), 3) if tn + fp else 0.0,
            "F1": round(2 * p * r / (p + r), 3) if p + r else 0.0}


def main(data: Path, out: Path = RESULTS_DIR, quiet: bool = False) -> dict:
    global OUT
    OUT = out
    truth = pd.read_json(data / "ground_truth.json")
    rows, packs, missing_rows, guard, ablation = [], {}, [], [], []
    print(f"validating {len(truth)} patients in {data} ...")
    for _, t in truth.iterrows():
        rec = load_workbook(data / f"{t.patient_id}.xlsx")
        res = analyze_record(rec)
        packs[t.patient_id] = res
        thr = threshold_alerts(rec)
        asked = {m["key"] for s in res["scenarios"] for m in s["missing_data"]}
        for s in res["scenarios"]:
            if not (s["status"] != "not_applicable"):
                continue
            rows.append({"patient_id": t.patient_id, "archetype": t.archetype, "sex": t.sex, "age": t.age,
                         "scenario": s["scenario"], "truth": s["scenario"] in t.expected_patterns,
                         "ours": bool(s["surfaced"]), "threshold": thr[s["scenario"]],
                         "linked": s["status"] == "pattern_with_context",
                         "context_truth": s["scenario"] in t.expected_context,
                         "pattern_start": s.get("pattern_start"), "planted_onset": t.planted_onset_date,
                         "status": s["status"]})
            text = s["explanation"]["text"]
            g = scenarios_config()["guardrails"]
            body = text.replace(g["required_disclaimer"], "").lower()
            guard.append({"banned": any(b in body for b in g["banned_phrases"]),
                          "disclaimer": g["required_disclaimer"] in text or s["status"] == "not_applicable"})
        if t.expected_missing:
            missing_rows.append({"patient_id": t.patient_id, "variant": t.missing_variant,
                                 "expected": t.expected_missing, "asked": sorted(asked),
                                 "all_asked": set(t.expected_missing) <= asked})
        # robustness: remove the whole wearable sheet from true t2d/htn patterns
        if t.archetype in ("t2d", "htn") and not isinstance(t.missing_variant, str):
            rec3 = load_workbook(data / f"{t.patient_id}.xlsx")
            rec3.sheets["wearable"] = pd.DataFrame()
            res3 = analyze_record(rec3)
            s3 = next(s for s in res3["scenarios"] if s["scenario"] == t.archetype)
            ablation.append({"patient_id": t.patient_id, "scenario": t.archetype, "still_surfaced": s3["surfaced"],
                             "asked_for_wearable": any(m["key"] in ("steps", "sleep_hours", "resting_hr") for m in s3["missing_data"]),
                             "status": s3["status"]})

    df = pd.DataFrame(rows)
    m = {"n_patients": int(len(truth)), "archetypes": truth.archetype.value_counts().to_dict(), "per_scenario": {}}
    for sc in SCEN:
        d = df[df.scenario == sc]
        m["per_scenario"][sc] = {"ours": prf(d, "ours"), "threshold_alert": prf(d, "threshold")}
    m["overall"] = {"ours": prf(df, "ours"), "threshold_alert": prf(df, "threshold")}

    stable = df[df.archetype.isin(STABLE)]
    pp = stable.groupby("patient_id").agg(ours=("ours", "any"), thr=("threshold", "any"), arch=("archetype", "first"))
    m["false_alarm_rate_stable_people"] = {
        "ours": round(pp.ours.mean(), 3), "threshold_alert": round(pp.thr.mean(), 3),
        "by_archetype": pp.groupby("arch")[["ours", "thr"]].mean().round(3).rename(columns={"thr": "threshold"}).to_dict(orient="index")}

    tp = df[df.ours & df.truth & df.pattern_start.notna() & df.planted_onset.notna()].copy()
    tp["lag_days"] = (pd.to_datetime(tp.pattern_start) - pd.to_datetime(tp.planted_onset)).dt.days
    m["onset_lag_days"] = {"median": float(tp.lag_days.median()) if len(tp) else 0.0, "p25": float(tp.lag_days.quantile(.25)),
                           "p75": float(tp.lag_days.quantile(.75)), "n": int(len(tp)),
                           "within_60_days": round(float((tp.lag_days.abs() <= 60).mean()), 3)}

    surfaced_true = df[df.ours & df.truth]
    m["context_linking_accuracy"] = {"accuracy": round(float((surfaced_true.linked == surfaced_true.context_truth).mean()), 3),
                                     "n": int(len(surfaced_true)),
                                     "drift_without_history_correctly_unlinked": int(((~surfaced_true.linked) & (~surfaced_true.context_truth)).sum()),
                                     "drift_without_history_total": int((~surfaced_true.context_truth).sum())}

    mr = pd.DataFrame(missing_rows)
    m["missing_data_requests"] = {"patients_with_removed_data": int(len(mr)),
                                  "all_removed_items_asked_for": round(float(mr.all_asked.mean()), 3) if len(mr) else None,
                                  "by_variant": mr.groupby("variant").all_asked.mean().round(3).to_dict() if len(mr) else {}}
    ab = pd.DataFrame(ablation)
    m["robustness_no_wearable_sheet"] = {"n": int(len(ab)),
                                         "still_surfaced": ab.groupby("scenario").still_surfaced.mean().round(3).to_dict() if len(ab) else {},
                                         "asked_for_wearable_data": round(float(ab.asked_for_wearable.mean()), 3) if len(ab) else None}
    gd = pd.DataFrame(guard)
    m["guardrails"] = {"explanations_checked": int(len(gd)), "with_banned_phrase": int(gd.banned.sum()),
                       "with_disclaimer": round(float(gd.disclaimer.mean()), 3)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "metrics.json").write_text(json.dumps(m, indent=2, default=str))
    df.to_csv(OUT / "validation_rows.csv", index=False)
    make_figures(m, tp)
    write_report(m, df, mr, ab)
    if not quiet:
        print(json.dumps({k: m[k] for k in ("overall", "false_alarm_rate_stable_people", "onset_lag_days")}, indent=1, default=str))
    return m


def make_figures(m, tp):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig_dir = OUT / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": GRAY, "axes.labelcolor": "#333", "xtick.color": "#555", "ytick.color": "#555"})

    # 1. precision / recall: our multi-signal method vs threshold alert
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    x = np.arange(len(SCEN))
    for ax, metric in zip(axes, ("precision", "recall")):
        ours = [m["per_scenario"][s]["ours"][metric] for s in SCEN]
        thr = [m["per_scenario"][s]["threshold_alert"][metric] for s in SCEN]
        b1 = ax.bar(x - 0.19, ours, 0.36, color=BLUE, label="Multi-signal (ours)")
        b2 = ax.bar(x + 0.19, thr, 0.36, color=ORANGE, label="Threshold alert")
        for bars in (b1, b2):
            for b in bars:
                ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02, f"{b.get_height():.2f}", ha="center", fontsize=8, color="#333")
        ax.set_xticks(x, ["Type 2 diabetes", "Hypertension", "PCOS"])
        ax.set_title(metric.capitalize(), loc="left", fontsize=11)
        ax.set_ylim(0, 1.12)
        ax.yaxis.grid(True, color="#e5e5e2")
        ax.set_axisbelow(True)
    fig.legend(*axes[0].get_legend_handles_labels(), frameon=False, fontsize=8, loc="lower center", ncol=2)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(fig_dir / "precision_recall_vs_threshold.png", dpi=160)
    plt.close(fig)

    # 2. false alarms on people with NO planted pattern
    fa = m["false_alarm_rate_stable_people"]["by_archetype"]
    names = list(fa)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    y = np.arange(len(names))
    ax.barh(y + 0.19, [fa[n]["ours"] for n in names], 0.36, color=BLUE, label="Multi-signal (ours)")
    ax.barh(y - 0.19, [fa[n]["threshold"] for n in names], 0.36, color=ORANGE, label="Threshold alert")
    for i, n in enumerate(names):
        ax.text(fa[n]["ours"] + 0.01, i + 0.19, f"{fa[n]['ours']:.0%}", va="center", fontsize=8)
        ax.text(fa[n]["threshold"] + 0.01, i - 0.19, f"{fa[n]['threshold']:.0%}", va="center", fontsize=8)
    ax.set_yticks(y, [n.replace("_", " ") for n in names])
    ax.set_xlim(0, 1.15)
    ax.set_title("Share of people with NO planted pattern who got flagged", loc="left", fontsize=11)
    ax.xaxis.grid(True, color="#e5e5e2")
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    fig.tight_layout()
    fig.savefig(fig_dir / "false_alarms.png", dpi=160)
    plt.close(fig)

    # 3. onset lag
    if len(tp):
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.hist(tp.lag_days, bins=range(-120, 181, 15), color=BLUE, edgecolor="white", linewidth=2)
        ax.axvline(0, color=GRAY, linestyle="--", linewidth=1)
        ax.set_xlabel("Detected start minus planted start (days)")
        ax.set_ylabel("Patterns")
        ax.set_title("When the pattern was dated vs. when we planted it", loc="left", fontsize=11)
        fig.tight_layout()
        fig.savefig(fig_dir / "onset_lag.png", dpi=160)
        plt.close(fig)


def pct(v) -> str:
    return "n/a" if v is None else f"{v:.0%}"


def write_report(m, df, mr, ab):
    def row(name, d):
        return f"| {name} | {d['precision']:.2f} | {d['recall']:.2f} | {d['specificity']:.2f} | {d['F1']:.2f} | {d['TP']} | {d['FP']} | {d['FN']} |"
    L = ["# Validation report (version 1)", "",
         f"Generated by `scripts/validate.py` on {m['n_patients']} synthetic workbooks with the real Prana Chain sheet layout "
         "and planted ground truth. Real workbooks have no labels, so accuracy can only be measured here; "
         "see `docs/VALIDATION.md` for how to read these numbers.", "",
         "## 1. Pattern detection vs. a threshold alert", "",
         "| Scenario / method | Precision | Recall | Specificity | F1 | TP | FP | FN |", "|---|---|---|---|---|---|---|---|"]
    for s in SCEN:
        L.append(row(f"{s} - multi-signal (ours)", m["per_scenario"][s]["ours"]))
        L.append(row(f"{s} - threshold alert", m["per_scenario"][s]["threshold_alert"]))
    L.append(row("**all - multi-signal (ours)**", m["overall"]["ours"]))
    L.append(row("**all - threshold alert**", m["overall"]["threshold_alert"]))
    fa = m["false_alarm_rate_stable_people"]
    L += ["", "![precision recall](figures/precision_recall_vs_threshold.png)", "",
          "## 2. False alarms on people with no planted pattern", "",
          f"Flagged at least once: **{fa['ours']:.0%} with our method vs {fa['threshold_alert']:.0%} with a threshold alert.**", "",
          "| Group | Ours | Threshold alert |", "|---|---|---|"]
    for k, v in fa["by_archetype"].items():
        L.append(f"| {k} | {v['ours']:.0%} | {v['threshold']:.0%} |")
    o = m["onset_lag_days"]
    c = m["context_linking_accuracy"]
    L += ["", "![false alarms](figures/false_alarms.png)", "",
          "## 3. Timing", "", f"Median detected start vs. planted start: **{o['median']:+.0f} days** "
          f"(IQR {o['p25']:+.0f} to {o['p75']:+.0f}); {o['within_60_days']:.0%} within 60 days (n={o['n']}).", "",
          "![onset lag](figures/onset_lag.png)", "",
          "## 4. Linking to history", "",
          f"For correctly surfaced patterns, 'linked to history' matched the truth in **{c['accuracy']:.0%}** of cases (n={c['n']}). "
          f"Drift without any history finding was correctly reported as *not linked* in {c['drift_without_history_correctly_unlinked']}"
          f"/{c['drift_without_history_total']} cases.", "",
          "## 5. Missing data", ""]
    md = m["missing_data_requests"]
    L.append(f"In {pct(md['all_removed_items_asked_for'])} of the {md['patients_with_removed_data']} patients where we removed data, "
             f"the system asked for every removed item. By variant: {md['by_variant']}.")
    rb = m["robustness_no_wearable_sheet"]
    L += ["", "## 6. Robustness: whole wearable sheet removed", "",
          f"Still surfaced (by scenario): {rb['still_surfaced']}. Asked the user for wearable data: {pct(rb.get('asked_for_wearable_data'))} (n={rb['n']}).",
          "Blood pressure comes from the Vitals sheet, so hypertension does not depend on the wearable; without it the diabetes pattern has to rest on weight + labs, so some subtle cases drop below 3 signals.", "",
          "## 7. Guardrails", ""]
    g = m["guardrails"]
    L += [f"{g['explanations_checked']} explanations checked: {g['with_banned_phrase']} contained banned wording; "
          f"{g['with_disclaimer']:.0%} carried the disclaimer.", "",
          "Wording is template-only in this checkpoint (LLM wording is planned for week 7).", "",
          ]
    errs = df[(df.ours != df.truth)]
    L += ["", "## 8. Every error, for the limitations section", "", "| Patient | Archetype | Scenario | Truth | Ours | Status |", "|---|---|---|---|---|---|"]
    for r in errs.itertuples():
        L.append(f"| {r.patient_id} | {r.archetype} | {r.scenario} | {r.truth} | {r.ours} | {r.status} |")
    (OUT / "validation_report.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("data/synthetic"))
    ap.add_argument("--out", type=Path, default=RESULTS_DIR)
    a = ap.parse_args()
    main(a.data, a.out)
