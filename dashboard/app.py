"""Prana Chain health-intelligence dashboard (owner: Tanusree).

    streamlit run dashboard/app.py          ->  http://localhost:8501
    open one patient directly:              ->  http://localhost:8501/?patient=SYN0001

Checkpoint version: one patient view = scenario cards, timeline vs personal
baseline, evidence + explanation, missing-data list, data quality.
Planned: cohort overview + validation pages (week 7), "add missing data and
re-run" form (week 8), patient vs clinician views (week 7).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from prana.analysis.baseline import rolling_view  # noqa: E402
from prana.config import RAW_DIR, RESULTS_DIR, SYNTHETIC_DIR  # noqa: E402
from prana.data.loader import list_workbooks  # noqa: E402
from prana.data.timeline import daily_series  # noqa: E402
from prana.insight.evidence import LABELS  # noqa: E402
from prana.insight.pipeline import analyze_workbook  # noqa: E402

st.set_page_config(page_title="Prana Chain · Health Intelligence", layout="wide")

BLUE, ORANGE, AQUA, VIOLET, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6", "#8a8984"
BADGE = {"pattern_with_context": ("Pattern linked to history", "#b54708", "#fef0e6"),
         "pattern_no_context": ("Pattern (no history link)", "#9a6700", "#fff6d6"),
         "known_context_stable": ("Known finding, stable", "#1d6b3a", "#e7f6ec"),
         "no_pattern": ("No pattern", "#3d3d3a", "#efefec"),
         "insufficient_data": ("Not enough data", "#3d3d3a", "#efefec"),
         "not_applicable": ("Not applicable", "#6b6b66", "#f5f5f2")}
PANELS = [("Blood pressure (mmHg)", ["sbp", "dbp"]), ("Weight (kg)", ["weight_kg"]), ("Steps / day", ["steps"]),
          ("Sleep (h)", ["sleep_hours"]), ("Resting HR (bpm)", ["resting_hr"])]
st.markdown("""<style>
.badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:0.8rem;font-weight:600}
.small{color:#6b6b66;font-size:0.85rem}
</style>""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Analysing workbook…")
def run(path: str):
    result, rec, tl = analyze_workbook(path)
    series = {sig: daily_series(rec, sig) for _, sigs in PANELS for sig in sigs}
    return result, tl, series


def badge(status):
    text, fg, bg = BADGE[status]
    return f'<span class="badge" style="color:{fg};background:{bg}">{text}</span>'


# ------------------------------------------------------------------ sidebar
st.sidebar.title("Prana Chain")
st.sidebar.caption("Team 8 · AI Health Intelligence · checkpoint")
sources = {"Real dataset (data/raw)": RAW_DIR, "Synthetic test set (data/synthetic)": SYNTHETIC_DIR}
available = {k: v for k, v in sources.items() if list_workbooks(v)}
if not available:
    st.error("No workbooks found. Put Prana Chain .xlsx files in data/raw, or run "
             "`python -m prana.data.generate_synthetic --n 120 --out data/synthetic`.")
    st.stop()
src_name = st.sidebar.selectbox("Data", list(available))
files = {p.stem: p for p in list_workbooks(available[src_name])}
summary_path = RESULTS_DIR / "summary.csv"
summary = pd.read_csv(summary_path) if summary_path.exists() else pd.DataFrame()

ids = list(files)
if not summary.empty and st.sidebar.checkbox("Only patients with a surfaced pattern", value=True):
    flagged = set(summary[summary.surfaced & summary.patient_id.isin(ids)].patient_id)
    ids = [i for i in ids if i in flagged] or list(files)
qp = st.query_params.get("patient")
if qp in files and qp not in ids:
    ids = [qp] + ids
pid = st.sidebar.selectbox("Patient", ids, index=ids.index(qp) if qp in ids else 0)

result, tl, series = run(str(files[pid]))
prof = result["profile"]
st.title(f"Patient {result['patient_id']}")
st.markdown(f"<span class='small'>{prof.get('Age', '?')} y · {prof.get('Sex', '?')} · data window "
            f"{' to '.join(result['window'] or [])} · family history: {prof.get('Family History', 'n/a')}</span>",
            unsafe_allow_html=True)
st.info("This tool describes patterns in your own data. It does not diagnose. Please discuss any pattern with your healthcare provider.")

# ------------------------------------------------------------------ scenario cards
for col, s in zip(st.columns(3), result["scenarios"]):
    with col:
        st.markdown(f"**{s['title']}**<br>{badge(s['status'])}", unsafe_allow_html=True)
        st.caption(s["status_text"])
        if s["surfaced"]:
            st.caption(f"{len(s['pattern_signals'])} signals moved together · from {s.get('pattern_start') or 'n/a'}")

tab_tl, tab_ev, tab_md, tab_q = st.tabs(["Timeline", "Evidence & explanation", "Missing data", "Data quality"])

# ------------------------------------------------------------------ timeline
with tab_tl:
    fig = make_subplots(rows=len(PANELS), cols=1, shared_xaxes=True, vertical_spacing=0.03,
                        subplot_titles=[p[0] for p in PANELS])
    for i, (_, sigs) in enumerate(PANELS, start=1):
        for j, sig in enumerate(sigs):
            s = series.get(sig)
            if s is None or s.dropna().empty:
                continue
            rv = rolling_view(s)
            color = BLUE if j == 0 else VIOLET
            if j == 0:
                fig.add_trace(go.Scatter(x=rv.index, y=rv["baseline_high"], line=dict(width=0), showlegend=False,
                                         hoverinfo="skip"), i, 1)
                fig.add_trace(go.Scatter(x=rv.index, y=rv["baseline_low"], fill="tonexty", fillcolor="rgba(138,137,132,0.15)",
                                         line=dict(width=0), name="personal baseline ±1 SD", showlegend=(i == 1),
                                         hoverinfo="skip"), i, 1)
            fig.add_trace(go.Scatter(x=rv.index, y=rv["value"], mode="markers", marker=dict(size=3, color=color, opacity=0.25),
                                     showlegend=False,
                                     hovertemplate=f"{LABELS.get(sig, sig)}: %{{y:.1f}}<br>%{{x|%d %b %Y}}<extra></extra>"), i, 1)
            fig.add_trace(go.Scatter(x=rv.index, y=rv["rolling"], mode="lines", line=dict(width=2, color=color),
                                     showlegend=False, hovertemplate="30-day mean: %{y:.1f}<extra></extra>"), i, 1)
    for d in sorted({s["pattern_start"] for s in result["scenarios"] if s["surfaced"] and s.get("pattern_start")}):
        fig.add_vline(x=d, line=dict(color=ORANGE, width=1.5, dash="dash"))
    fig.update_layout(height=900, margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified",
                      plot_bgcolor="white", legend=dict(orientation="h", y=1.04))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#eeeeea")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Dots = daily readings · line = 30-day mean · grey band = your first-60-day baseline ±1 SD · "
               "orange dashed = detected pattern start.")
    labs = tl[tl.source == "lab"]
    key_labs = labs[labs.signal.isin(["hba1c", "fasting_glucose", "ldl_cholesterol", "testosterone", "triglycerides"])]
    if not key_labs.empty:
        lf = go.Figure()
        for k, c in zip(key_labs.signal.unique(), [BLUE, ORANGE, AQUA, VIOLET, GRAY]):
            d = key_labs[key_labs.signal == k]
            lf.add_trace(go.Scatter(x=d.date, y=d.value, mode="lines+markers+text", name=LABELS.get(k, k),
                                    line=dict(color=c, width=2), marker=dict(size=8),
                                    text=[f"{v:g}" for v in d.value], textposition="top center"))
        lf.update_layout(height=320, title="Key lab results", plot_bgcolor="white", margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(lf, use_container_width=True)
    with st.expander("History, medications and symptoms on the same timeline"):
        st.dataframe(tl[tl.source.isin(["history", "medications", "symptoms"])][["date", "source", "text"]],
                     use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ evidence
with tab_ev:
    for s in result["scenarios"]:
        if s["status"] == "not_applicable":
            continue
        with st.expander(f"{s['title']} — {BADGE[s['status']][0]}", expanded=s["surfaced"]):
            st.markdown(s["explanation"]["text"])
            if s["evidence"]:
                st.markdown("**Evidence used**")
                st.dataframe(pd.DataFrame([{
                    "Signal": e["label"], "Type": e["kind"], "Earlier": e.get("baseline_mean", e.get("first")),
                    "Recent": e.get("recent_mean", e.get("last")), "Change": e.get("change"), "Change %": e.get("change_pct"),
                    "Effect size (SD)": e.get("effect_size"), "Trend p": e.get("trend_p"), "Started": e.get("onset_date")}
                    for e in s["evidence"]]), use_container_width=True, hide_index=True)
            if s["context"]:
                st.markdown("**Linked history / context**")
                st.dataframe(pd.DataFrame(s["context"]), use_container_width=True, hide_index=True)
            st.markdown("**All signals checked**")
            st.dataframe(pd.DataFrame([{"Signal": LABELS.get(k, k), "Status": a["status"], "Direction of concern": a["direction"],
                                        "Change": a.get("change"), "Coverage": a.get("coverage")}
                                       for k, a in s["signals"].items()]), use_container_width=True, hide_index=True)
            st.markdown("**Limitations**")
            for lim in s["limitations"]:
                st.markdown(f"- {lim}")

# ------------------------------------------------------------------ missing data
with tab_md:
    asks = [(s["title"], m) for s in result["scenarios"] for m in s["missing_data"]]
    if not asks:
        st.success("Nothing important is missing for these three areas.")
    for title, m in asks:
        st.markdown(f"- **{m['item']}** — {m['reason']} <span class='small'>({title})</span>", unsafe_allow_html=True)
    st.caption("Planned for week 8: add the requested data here and re-run the analysis.")

with tab_q:
    st.json(result["quality"])
