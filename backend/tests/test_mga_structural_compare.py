from __future__ import annotations

from app.services.lavaan_service import _inject_equal_label_for_regression


def test_inject_equal_label_for_regression_replaces_target_predictor_term():
    syntax = "\n".join(
        [
            "Y ~ X + Z",
            "M ~ X",
            "Y ~~ Y",
        ]
    )

    out = _inject_equal_label_for_regression(
        lavaan_syntax=syntax,
        outcome="Y",
        predictor="X",
        n_groups=3,
        label="b",
    )

    # only Y ~ ... is modified; X term is wrapped into c(b,b,b)*X
    compact = out.replace(" ", "")
    assert "Y~c(b,b,b)*X+Z" in compact
    assert "M ~ X" in out
