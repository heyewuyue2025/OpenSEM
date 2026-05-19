import pandas as pd


def test_build_invariance_series_summary_df_empty():
    from app.api.v1.export import _build_invariance_series_summary_df

    df = _build_invariance_series_summary_df(summary_lines=None, conclusion=None)
    assert df is None


def test_build_invariance_series_summary_df_lines_and_conclusion():
    from app.api.v1.export import _build_invariance_series_summary_df

    df = _build_invariance_series_summary_df(
        summary_lines=["a", " ", "b"],
        conclusion={
            "lite": {"level": "scalar", "ok": True, "note": "lite ok"},
            "strict": {"level": "strict", "ok": False, "note": "strict fail"},
        },
    )
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    # should include 2 conclusion rows + 2 summary lines (a,b)
    assert (df["type"] == "conclusion").sum() == 2
    assert (df["type"] == "summary_line").sum() == 2
    assert set(df["scope"].unique()) >= {"lite", "strict", "all"}


def test_build_invariance_series_report_df_empty():
    from app.api.v1.export import _build_invariance_series_report_df

    assert _build_invariance_series_report_df(None) is None
    assert _build_invariance_series_report_df({}) is None
    assert _build_invariance_series_report_df({"lite": "  ", "strict": ""}) is None


def test_build_invariance_series_report_df_lite_and_strict_lines():
    from app.api.v1.export import _build_invariance_series_report_df

    df = _build_invariance_series_report_df({"lite": "l1\nl2", "strict": "s1"})
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert set(df["scope"].unique()) == {"lite", "strict"}
    assert (df["scope"] == "lite").sum() == 2
    assert (df["scope"] == "strict").sum() == 1
    assert (df["type"] == "report_line").all()
