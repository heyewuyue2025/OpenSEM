import pandas as pd


def test_build_path_summary_df_empty():
    from app.api.v1.export import _build_path_summary_df

    df = _build_path_summary_df(rows=None, summary_lines=None, report_text=None)
    assert df is None


def test_build_path_summary_df_rows_and_text():
    from app.api.v1.export import _build_path_summary_df

    df = _build_path_summary_df(
        rows=[
            {
                "predictor": "X",
                "outcome": "Y",
                "op": "~",
                "beta": 0.1234,
                "p_value": 0.04,
                "significant": True,
                "direction": "positive",
                "note": "",
            }
        ],
        summary_lines=["显著性门槛：p<0.05"],
        report_text="【结构路径显著性汇总】\nX → Y（β=0.123，p=0.04）",
    )
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert (df["type"] == "path").sum() == 1
    assert (df["type"] == "summary_line").sum() == 1
    assert (df["type"] == "report_line").sum() >= 1

