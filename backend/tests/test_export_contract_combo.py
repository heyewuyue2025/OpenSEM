from io import BytesIO

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _combo_payload(data_key: str) -> dict:
    return {
        "data_key": data_key,
        "export_template": "journal_minimal_cn",
        "lavaan_syntax": "F1 =~ x1 + x2\nY ~ F1",
        "fit_indices": {"chi2": 10.2, "chi2_df": 1.8, "rmsea": 0.04, "srmr": 0.03, "cfi": 0.95, "tli": 0.94, "status": "good"},
        "estimates": [{"lval": "Y", "op": "~", "rval": "F1", "estimate": 0.32, "est_std": 0.31, "std_err": 0.08, "z_value": 3.9, "p_value": 0.001}],
        "bootstrap": {
            "covariates": ["age"],
            "items": [{"effect_type": "indirect", "label": "X->M->Y", "indirect_point": 0.2, "ci": {"ci_level": 0.95, "percentile": {"lo": 0.1, "hi": 0.3}, "bc": {"lo": 0.11, "hi": 0.29}, "n_boot_valid": 2000}}],
        },
        "moderation": {
            "predictor": "X",
            "outcome": "Y",
            "moderator": {"name": "W", "type": "continuous"},
            "coefficients": [{"term": "X:W", "estimate": 0.11, "std_err": 0.04, "z_value": 2.7, "p_value": 0.007}],
            "simple_slopes": [{"group": "W=+1SD", "slope_x": 0.34, "note": "sig"}],
        },
        "moderated_mediation": {
            "model": "hayes_model_7",
            "x": "X",
            "m": "M",
            "y": "Y",
            "w": "W",
            "conditional_indirect": [{"label": "W=mean", "w_value": 0.0, "indirect_point": 0.12, "ci": {"ci_level": 0.95, "percentile": {"lo": 0.03, "hi": 0.21}, "bc": {"lo": 0.04, "hi": 0.22}, "n_boot_valid": 2000}}],
        },
        "invariance_series": {"mode": "lavaan", "supported": True, "models": [{"model": "configural", "group_equal": [], "fit": {"chi2": 100, "df": 50, "cfi": 0.93, "tli": 0.92, "rmsea": 0.05, "srmr": 0.04}, "converged": True}], "comparisons": [{"from": "configural", "to": "metric", "ok": True, "chi2_diff": 2.1, "df_diff": 1, "p_value": 0.15, "delta_cfi": -0.001, "delta_rmsea": 0.001, "note": ""}]},
        "path_summary_rows": [{"predictor": "F1", "outcome": "Y", "op": "~", "beta": 0.31, "p_value": 0.002, "significant": True, "direction": "positive", "note": ""}],
        "model_comparison": {"mode": "lavaan", "supported": True, "models": [{"label": "m1", "fit": {"aic": 100, "bic": 120, "chi2": 10, "df": 8, "cfi": 0.95, "tli": 0.94, "rmsea": 0.04, "srmr": 0.03}}], "comparison": {"from": "m0", "to": "m1", "ok": True, "chi2_diff": 1.1, "df_diff": 1, "p_value": 0.29, "note": ""}},
        "mga_structural": {"mode": "lavaan", "supported": True, "items": [{"level": "configural", "path": {"predictor": "X", "outcome": "Y"}, "group_estimates": [{"group": "A", "estimate": 0.2, "std_all": 0.3, "p_value": 0.04, "note": ""}], "comparison": {"from": "free", "to": "eq", "ok": True, "chi2_diff": 0.8, "df_diff": 1, "p_value": 0.36, "note": ""}}]},
        "fit_stale": False,
    }


def test_export_combo_contract_success(monkeypatch):
    from app.api.v1 import export as export_module

    monkeypatch.setattr(export_module, "get_data", lambda _key: pd.DataFrame({"x1": [1.0], "x2": [2.0], "Y": [3.0]}))

    resp = client.post("/api/v1/export/apa-table", json=_combo_payload("valid-key"))
    assert resp.status_code == 200

    xls = pd.ExcelFile(BytesIO(resp.content))
    expected_sheets = {
        "Fit_Indices",
        "Estimates",
        "Model_Syntax",
        "Meta",
        "Bootstrap",
        "Moderation",
        "ModMediation",
        "Invariance_Series_Models",
        "Invariance_Series_LRT",
        "Path_Summary",
        "Model_Compare_Models",
        "Model_Compare_LRT",
        "MGA_Structural_Path",
        "MGA_Structural_LRT",
    }
    assert expected_sheets.issubset(set(xls.sheet_names))


def test_export_combo_contract_failure_invalid_data_key(monkeypatch):
    from app.api.v1 import export as export_module

    monkeypatch.setattr(export_module, "get_data", lambda _key: None)

    resp = client.post("/api/v1/export/apa-table", json=_combo_payload("invalid-key"))
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "EXPORT_DATA_KEY_INVALID"


def test_export_template_selection_is_traceable(monkeypatch):
    from app.api.v1 import export as export_module

    monkeypatch.setattr(export_module, "get_data", lambda _key: pd.DataFrame({"x1": [1.0], "x2": [2.0], "Y": [3.0]}))

    resp = client.post("/api/v1/export/apa-table", json=_combo_payload("valid-key"))
    assert resp.status_code == 200

    xls = pd.ExcelFile(BytesIO(resp.content))
    meta_df = pd.read_excel(xls, sheet_name="Meta")
    template_key = meta_df.loc[meta_df["Item"] == "Export Template Key", "Value"].iloc[0]
    template_name = meta_df.loc[meta_df["Item"] == "Export Template Name", "Value"].iloc[0]
    assert template_key == "journal_minimal_cn"
    assert template_name == "期刊模板（最小版）"


def test_export_template_selection_failure_unsupported_template(monkeypatch):
    from app.api.v1 import export as export_module

    monkeypatch.setattr(export_module, "get_data", lambda _key: pd.DataFrame({"x1": [1.0], "x2": [2.0], "Y": [3.0]}))
    payload = _combo_payload("valid-key")
    payload["export_template"] = "unknown_template"

    resp = client.post("/api/v1/export/apa-table", json=payload)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "EXPORT_TEMPLATE_UNSUPPORTED"
