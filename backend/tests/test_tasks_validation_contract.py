from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_bootstrap_mediation_rejects_too_small_n_boot():
    resp = client.post(
        "/api/v1/tasks/bootstrap-mediation",
        json={
            "data_key": "demo",
            "lavaan_syntax": "Y ~ X",
            "effects": [{"x": "X", "m": "M", "y": "Y"}],
            "n_boot": 10,
        },
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"


def test_bootstrap_mediation_rejects_invalid_ci_level():
    resp = client.post(
        "/api/v1/tasks/bootstrap-mediation",
        json={
            "data_key": "demo",
            "lavaan_syntax": "Y ~ X",
            "effects": [{"x": "X", "m": "M", "y": "Y"}],
            "ci_level": 1.2,
        },
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"


def test_moderation_analysis_rejects_invalid_moderator_type():
    resp = client.post(
        "/api/v1/tasks/moderation-analysis",
        json={
            "data_key": "demo",
            "x": "X",
            "w": "W",
            "y": "Y",
            "moderator_type": "binary_like",
        },
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"


def test_model_compare_rejects_blank_data_key():
    resp = client.post(
        "/api/v1/tasks/model-compare",
        json={
            "data_key": "   ",
            "lavaan_syntax_a": "Y ~ X",
            "lavaan_syntax_b": "Y ~~ X",
        },
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"


def test_model_compare_rejects_invalid_missing_strategy():
    resp = client.post(
        "/api/v1/tasks/model-compare",
        json={
            "data_key": "demo",
            "lavaan_syntax_a": "Y ~ X",
            "lavaan_syntax_b": "Y ~~ X",
            "missing_strategy": "pairwise",
        },
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"


def test_mga_structural_rejects_neither_paths_nor_legacy_pair():
    resp = client.post(
        "/api/v1/tasks/mga-structural-path-compare",
        json={
            "data_key": "demo",
            "lavaan_syntax": "Y ~ X",
            "group_var": "G",
            "outcome": "",
            "predictor": "",
        },
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"


def test_mga_structural_rejects_invalid_path_item():
    resp = client.post(
        "/api/v1/tasks/mga-structural-path-compare",
        json={
            "data_key": "demo",
            "lavaan_syntax": "Y ~ X",
            "group_var": "G",
            "paths": [{"predictor": "", "outcome": "Y"}],
        },
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"


def test_invariance_configural_rejects_max_groups_out_of_range():
    resp = client.post(
        "/api/v1/tasks/invariance-configural",
        json={
            "data_key": "demo",
            "lavaan_syntax": "Y ~ X",
            "group_var": "G",
            "max_groups": 200,
        },
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"


def test_invariance_lavaan_series_rejects_blank_group_var():
    resp = client.post(
        "/api/v1/tasks/invariance-lavaan-series",
        json={
            "data_key": "demo",
            "lavaan_syntax": "Y ~ X",
            "group_var": "  ",
        },
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"


def test_latent_interaction_probe_rejects_invalid_estimator():
    resp = client.post(
        "/api/v1/tasks/latent-interaction-probe",
        json={
            "data_key": "demo",
            "lavaan_syntax": "Y ~ F1 + F2 + F1:F2",
            "y": "Y",
            "f1": "F1",
            "f2": "F2",
            "estimator": "WLSMV",
        },
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"
