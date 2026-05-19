import numpy as np
import pandas as pd

from app.tasks.stats_tasks import (
    run_observed_moderated_mediation_model14,
    run_observed_moderated_mediation_model7,
)


def test_moderated_mediation_model7_returns_conditional_indirect_and_index():
    rng = np.random.default_rng(42)
    n = 250
    x = rng.standard_normal(n)
    w = rng.standard_normal(n)
    m = 0.4 * x + 0.2 * w + 0.35 * (x * w) + rng.standard_normal(n) * 0.15
    y = 0.5 * m + 0.15 * x + 0.1 * w + rng.standard_normal(n) * 0.15
    df = pd.DataFrame({"X": x, "M": m, "Y": y, "W": w})

    out = run_observed_moderated_mediation_model7(
        df,
        "X",
        "M",
        "Y",
        "W",
        covariates=None,
        n_boot=300,
        ci_level=0.95,
        seed=7,
    )

    assert out["success"] is True
    assert out["model"] == "hayes_process_7"
    assert len(out["conditional_indirect"]) == 3
    assert out["index_moderated_mediation"]["point"] is not None
    for row in out["conditional_indirect"]:
        assert row["label"]
        assert row["ci"] is not None


def test_moderated_mediation_model7_categorical_w():
    rng = np.random.default_rng(1)
    n = 200
    g = np.array(["A"] * 100 + ["B"] * 100)
    x = rng.standard_normal(n)
    w_dummy = (g == "B").astype(float)
    m = 0.35 * x + 0.25 * (x * w_dummy) + rng.standard_normal(n) * 0.2
    y = 0.45 * m + 0.1 * x + rng.standard_normal(n) * 0.2
    df = pd.DataFrame({"X": x, "M": m, "Y": y, "G": g})

    out = run_observed_moderated_mediation_model7(
        df,
        "X",
        "M",
        "Y",
        "G",
        covariates=None,
        n_boot=250,
        ci_level=0.95,
        seed=3,
        w_type="categorical",
    )
    assert out["success"] is True
    assert out["model"] == "hayes_process_7_categorical"
    assert len(out["conditional_indirect"]) == 2
    assert out["index_moderated_mediation"]["point"] is not None
    assert out["moderator_meta"]["reference_group"] == "A"


def test_moderated_mediation_model14_continuous_w():
    rng = np.random.default_rng(2)
    n = 220
    x = rng.standard_normal(n)
    w = rng.standard_normal(n)
    m = 0.5 * x + rng.standard_normal(n) * 0.15
    y = 0.4 * m + 0.2 * w + 0.35 * (m * w) + 0.1 * x + rng.standard_normal(n) * 0.15
    df = pd.DataFrame({"X": x, "M": m, "Y": y, "W": w})

    out = run_observed_moderated_mediation_model14(
        df,
        "X",
        "M",
        "Y",
        "W",
        covariates=None,
        n_boot=280,
        ci_level=0.95,
        seed=11,
    )
    assert out["success"] is True
    assert out["model"] == "hayes_process_14"
    assert len(out["conditional_indirect"]) == 3
    assert out["index_moderated_mediation"]["point"] is not None
