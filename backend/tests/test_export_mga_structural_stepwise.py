import pandas as pd


def test_build_mga_structural_dfs_wave3_items():
    from app.api.v1.export import _build_mga_structural_dfs

    mga = {
        "mode": "lavaan",
        "supported": True,
        "group_var": "G",
        "items": [
            {
                "level": "configural",
                "path": {"predictor": "X", "outcome": "Y"},
                "group_estimates": [
                    {"group": "A", "estimate": 0.1, "std_all": 0.2, "p_value": 0.03, "note": ""},
                    {"group": "B", "estimate": 0.2, "std_all": 0.3, "p_value": 0.04, "note": ""},
                ],
                "comparison": {"from": "configural:free", "to": "configural:constrained", "ok": True, "chi2_diff": 1.2, "df_diff": 1, "p_value": 0.27, "note": ""},
            }
        ],
    }

    path_df, lrt_df = _build_mga_structural_dfs(mga)
    assert isinstance(path_df, pd.DataFrame)
    assert isinstance(lrt_df, pd.DataFrame)
    assert not path_df.empty
    assert not lrt_df.empty
    assert list(path_df.columns) == ["level", "predictor", "outcome", "group", "estimate", "std_all", "p_value", "note"]
    assert list(lrt_df.columns) == ["level", "predictor", "outcome", "from", "to", "ok", "chi2_diff", "df_diff", "p_value", "note"]


def test_build_mga_structural_dfs_wave2_compatible():
    from app.api.v1.export import _build_mga_structural_dfs

    mga = {
        "mode": "degraded",
        "supported": False,
        "group_var": "G",
        "path": {"predictor": "X", "outcome": "Y"},
        "group_estimates": [
            {"group": "A", "coef": {"estimate": 0.1, "std_all": 0.2, "p_value": 0.03}},
        ],
        "comparison": {"from": "free", "to": "constrained", "ok": False, "chi2_diff": None, "df_diff": None, "p_value": None, "note": "degraded"},
    }

    path_df, lrt_df = _build_mga_structural_dfs(mga)
    assert isinstance(path_df, pd.DataFrame)
    assert isinstance(lrt_df, pd.DataFrame)
    assert list(path_df.columns) == ["group", "estimate", "std_all", "p_value", "note"]
    assert list(lrt_df.columns) == ["from", "to", "ok", "chi2_diff", "df_diff", "p_value", "note"]

