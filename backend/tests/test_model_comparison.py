from __future__ import annotations

import pandas as pd

from app.tasks.stats_tasks import run_semopy_model_compare


def test_run_semopy_model_compare_returns_stable_schema():
    df = pd.DataFrame(
        {
            "X": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
            "Z": [1.0, 0.0, 1.5, 2.0, 2.5, 3.0],
        }
    )
    df["Y"] = 1.0 + 0.6 * df["X"] + 0.2 * df["Z"]

    # A 更复杂（嵌套）：Y ~ X + Z
    syntax_a = "Y ~ X + Z"
    # B 更简化：Y ~ X
    syntax_b = "Y ~ X"

    out = run_semopy_model_compare(
        data=df,
        syntax_a=syntax_a,
        syntax_b=syntax_b,
        estimator="ML",
        missing_strategy="listwise",
        label_a="Full",
        label_b="Reduced",
    )

    assert out["mode"] == "semopy"
    assert isinstance(out["models"], list)
    assert len(out["models"]) == 2
    assert out["models"][0]["label"] == "Full"
    assert out["models"][1]["label"] == "Reduced"
    for m in out["models"]:
        fit = m.get("fit") or {}
        for k in ["aic", "bic", "chi2", "df", "cfi", "tli", "rmsea", "srmr"]:
            assert k in fit

    comp = out.get("comparison") or {}
    assert comp.get("from") == "Full"
    assert comp.get("to") == "Reduced"
    assert comp.get("ok") is False
