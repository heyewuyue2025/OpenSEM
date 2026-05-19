from __future__ import annotations

import pandas as pd

from app.tasks.stats_tasks import run_observed_moderation_analysis


def test_observed_moderation_returns_interaction_term_for_continuous_moderator():
    df = pd.DataFrame(
        {
            "X": [0, 1, 2, 3, 4, 5, 6, 7],
            "W": [0, 1, 0, 1, 0, 1, 0, 1],
            "C1": [10, 11, 9, 10, 12, 13, 8, 9],
        }
    )
    df["Y"] = 1.0 + 0.5 * df["X"] + 0.2 * df["W"] + 1.5 * df["X"] * df["W"] + 0.3 * df["C1"]

    result = run_observed_moderation_analysis(
        df=df,
        x="X",
        w="W",
        y="Y",
        moderator_type="continuous",
        covariates=["C1"],
    )

    coef_names = [row["term"] for row in result["coefficients"]]
    assert "X" in coef_names
    assert "W" in coef_names
    assert "X×W" in coef_names
    assert "C1" in coef_names
    interaction = next(row for row in result["coefficients"] if row["term"] == "X×W")
    assert abs(interaction["estimate"] - 1.5) < 1e-6
    assert result["interaction"]["term"] == "X×W"
    assert result["moderator"]["type"] == "continuous"


def test_observed_moderation_expands_categorical_moderator_and_group_slopes():
    df = pd.DataFrame(
        {
            "X": [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3],
            "W": ["A", "A", "A", "A", "B", "B", "B", "B", "C", "C", "C", "C"],
            "C1": [10, 11, 12, 13, 9, 9, 10, 11, 8, 8, 9, 10],
        }
    )
    slope_map = {"A": 0.5, "B": 1.0, "C": 1.5}
    intercept_map = {"A": 1.0, "B": 1.2, "C": 1.4}
    df["Y"] = [
        intercept_map[w] + slope_map[w] * x + 0.2 * c1 for x, w, c1 in zip(df["X"], df["W"], df["C1"])
    ]

    result = run_observed_moderation_analysis(
        df=df,
        x="X",
        w="W",
        y="Y",
        moderator_type="categorical",
        covariates=["C1"],
    )

    coef_names = [row["term"] for row in result["coefficients"]]
    assert "W[B]" in coef_names
    assert "W[C]" in coef_names
    assert "X×W[B]" in coef_names
    assert "X×W[C]" in coef_names
    assert "C1" in coef_names
    assert result["moderator"]["reference_group"] == "A"

    simple_slopes = {row["group"]: row["slope_x"] for row in result["simple_slopes"]}
    assert abs(simple_slopes["A"] - 0.5) < 1e-6
    assert abs(simple_slopes["B"] - 1.0) < 1e-6
    assert abs(simple_slopes["C"] - 1.5) < 1e-6
