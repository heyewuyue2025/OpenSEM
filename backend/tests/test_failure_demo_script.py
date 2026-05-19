import importlib.util
from pathlib import Path


def _load_failure_demo_module():
    root = Path(__file__).resolve().parents[2]
    script_path = root / "demo" / "run_failure_demo.py"
    assert script_path.is_file(), f"缺少失败演示脚本: {script_path}"
    spec = importlib.util.spec_from_file_location("run_failure_demo", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_failure_contract_check_success_cases():
    mod = _load_failure_demo_module()
    ok, issues = mod.check_failure_contract(
        {
            "validate_key_invalid": {"status": 200, "body": {"valid": False}},
            "export_invalid_key": {"status": 400, "body": {"detail": {"code": "EXPORT_DATA_KEY_INVALID"}}},
            "model_compare_validation_error": {"status": 422, "body": {"detail": {"code": "VALIDATION_ERROR"}}},
        }
    )
    assert ok is True
    assert issues == []


def test_failure_contract_check_fails_on_wrong_code():
    mod = _load_failure_demo_module()
    ok, issues = mod.check_failure_contract(
        {
            "validate_key_invalid": {"status": 200, "body": {"valid": True}},
            "export_invalid_key": {"status": 400, "body": {"detail": {"code": "WRONG_CODE"}}},
            "model_compare_validation_error": {"status": 422, "body": {"detail": {"code": "VALIDATION_ERROR"}}},
        }
    )
    assert ok is False
    assert len(issues) >= 1
    assert any("validate-key" in item or "EXPORT_DATA_KEY_INVALID" in item for item in issues)
