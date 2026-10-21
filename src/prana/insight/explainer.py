"""Plain-language explanation layer (owner: Uday).

Checkpoint version: deterministic TEMPLATE wording only. Every sentence is
built from numbers already in the evidence pack, so nothing can be invented.

Planned (week 7): an LLM (HIPAA-eligible route) may reword the anonymised
evidence pack; its output will be checked for banned wording and for numbers
that are not in the pack before it is shown. See docs/PLAN_AND_DISCUSSION.md.
"""
from __future__ import annotations

import pandas as pd

from prana.config import scenarios_config

DIRECTION_WORD = {("daily", "up"): "rose", ("daily", "down"): "fell", ("lab", "up"): "went up",
                  ("lab", "down"): "went down", ("cycle", "up"): "became longer"}


def _fmt(v, signal: str) -> str:
    if v is None:
        return "n/a"
    if signal == "steps":
        return f"{v:,.0f}"
    if abs(v) >= 100:
        return f"{v:.0f}"
    return f"{v:.1f}" if signal not in ("hba1c", "lh_fsh_ratio") else f"{v:.2f}"


def _month(d: str | None) -> str:
    return pd.Timestamp(d).strftime("%B %Y") if d else "the recent months"


def template_explanation(pack: dict) -> str:
    g = scenarios_config()["guardrails"]
    st = pack["status"]
    if st == "not_applicable":
        return "This area does not apply to this person's profile."
    lines = []
    if st in ("pattern_with_context", "pattern_no_context"):
        lines.append(f"**{pack['title']}: a pattern worth discussing.** Starting around {_month(pack.get('pattern_start'))}, "
                     f"{len(pack['evidence'])} related measurements moved in the same direction compared with your own earlier levels:")
        for e in pack["evidence"]:
            word = DIRECTION_WORD.get((e["kind"], e["direction"]), "changed")
            if e["kind"] == "lab":
                vals = ", ".join(_fmt(v["value"], e["signal"]) for v in e["values"])
                lines.append(f"- {e['label']} {word}: results over the year were {vals}.")
            elif e["kind"] == "cycle":
                lines.append(f"- {e['label']} {word}: about {_fmt(e['baseline_mean'], 'x')} days at the start, "
                             f"about {_fmt(e['recent_mean'], 'x')} days in the most recent cycles.")
            else:
                pct = f" ({e['change_pct']:+.0f}%)" if e.get("change_pct") is not None else ""
                lines.append(f"- {e['label']} {word} from about {_fmt(e['baseline_mean'], e['signal'])} "
                             f"to about {_fmt(e['recent_mean'], e['signal'])}{pct}, from around {_month(e['onset_date'])}.")
    elif st == "known_context_stable":
        lines.append(f"**{pack['title']}: no new pattern.** There is a related item in your history, "
                     "and your ongoing measurements have stayed close to your usual levels.")
    elif st == "insufficient_data":
        lines.append(f"**{pack['title']}: not enough data yet** to look for a pattern.")
    else:
        lines.append(f"**{pack['title']}: no multi-signal pattern found.**")
        if pack["changed_signals"]:
            lines.append("One or two measurements changed on their own (" +
                         ", ".join(e["label"] for e in pack["evidence"]) + "), which is shown on the timeline but is not treated as a pattern.")

    prior = [c for c in pack["context"] if c["type"] != "symptoms"]
    if prior:
        lines.append("**Why this may matter for you:** your record already includes " +
                     "; ".join(f"{c['text']}" + (f" ({c['date']})" if c['date'] else "") for c in prior[:4]) + ".")
    sym = [c for c in pack["context"] if c["type"] == "symptoms"]
    if sym and st in ("pattern_with_context", "pattern_no_context"):
        lines.append(f"You also logged related symptoms: {sym[0]['text']}.")
    if pack["missing_data"]:
        lines.append("**What would make this clearer:** " +
                     "; ".join(f"{m['item']} ({m['reason']})" for m in pack["missing_data"]) + ".")
    lines.append(f"_{g['required_disclaimer']}_")
    return "\n\n".join(lines)


def explain(pack: dict) -> dict:
    return {"text": template_explanation(pack), "source": "template"}
