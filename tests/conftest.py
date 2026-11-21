import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prana.data.generate_synthetic import make_patient  # noqa: E402


@pytest.fixture(scope="session")
def workbooks(tmp_path_factory):
    """One small workbook per archetype, written with the real sheet layout."""
    out = tmp_path_factory.mktemp("wb")
    rng = np.random.default_rng(42)
    plan = {"t2d": None, "htn": None, "pcos": None, "control": None, "single_signal": None,
            "t2d_missing": "no_recent_hba1c", "pcos_nohormones": "no_hormone_labs"}
    paths = {}
    for name, missing in plan.items():
        arch = name.split("_")[0] if name not in ("single_signal",) else name
        sheets, truth = make_patient(f"T{len(paths):03d}", arch, rng, missing)
        if name == "control":  # make sure the control is male, so PCOS is not applicable
            sheets["Patient Profile"].loc[sheets["Patient Profile"].Field == "Sex", "Value"] = "Male"
        p = out / f"{name}.xlsx"
        with pd.ExcelWriter(p, engine="openpyxl") as xw:
            for sn, df in sheets.items():
                df.to_excel(xw, sheet_name=sn, index=False)
        paths[name] = p
    return paths


@pytest.fixture(autouse=True)
def _no_real_model_in_tests(monkeypatch):
    """Tests never read the project's real .env or call a real model: a developer's key must not change a test result or be spent by one."""
    from prana import config
    monkeypatch.setattr(config, "_dotenv", lambda: {})
    for name in ("PRANA_LLM", "PRANA_LLM_URL", "PRANA_LLM_MODEL", "PRANA_LLM_KEY", "PRANA_LLM_REASONING", "PRANA_LLM_REWORD", "PRANA_LLM_TIMEOUT", "PRANA_EXTRACT_AI", "PRANA_ADMIN_IDS", "ANTHROPIC_API_KEY", "GUEST_ID"):
        monkeypatch.delenv(name, raising=False)
    import os
    for name in [n for n in os.environ if n.startswith(("PRANA_MEDGEMMA_", "PRANA_RERANK_"))]:   # the same guard for the MedGemma and rerank settings
        monkeypatch.delenv(name, raising=False)
