import pandas as pd


def test_flatten_invariance_estimates_empty():
    from app.api.v1.export import _flatten_invariance_estimates

    df = _flatten_invariance_estimates([])
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_flatten_invariance_estimates_basic():
    from app.api.v1.export import _flatten_invariance_estimates

    df = _flatten_invariance_estimates(
        [
            {
                "group": "A",
                "estimates": [
                    {"lval": "Y", "op": "~", "rval": "X", "estimate": 0.1, "est_std": 0.2, "p_value": 0.04},
                    {"lval": "F1", "op": "=~", "rval": "x1", "estimate": 1.0, "est_std": 0.8, "p_value": 0.0},
                ],
            },
            {"group": "B", "estimates": []},
        ]
    )
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert set(df.columns) >= {"group", "lval", "op", "rval", "estimate", "est_std", "p_value"}
    assert (df["group"] == "A").all()

