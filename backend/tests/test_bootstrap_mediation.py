import pytest

from app.tasks.stats_tasks import (
    _build_total_indirect_rows,
    _compute_indirect_effect,
    _normalize_effect_spec,
    _parse_sequence_text,
    _validate_effect_specs_allowlist,
    _augment_lavaan_syntax_with_covariates,
)


def test_normalize_effect_spec_keeps_legacy_single_mediator_shape():
    spec = _normalize_effect_spec({"x": "X", "m": "M", "y": "Y"})

    assert spec is not None
    assert spec["sequence"] == ["X", "M", "Y"]
    assert spec["mediators"] == ["M"]
    assert spec["effect_type"] == "specific_indirect"


def test_compute_indirect_effect_supports_chain_mediation():
    path_map = {
        "M1 ~ X": 0.5,
        "M2 ~ M1": 0.4,
        "Y ~ M2": 0.3,
    }

    effect = _compute_indirect_effect(path_map, ["X", "M1", "M2", "Y"])

    assert effect == 0.06


def test_build_total_indirect_rows_sums_parallel_specific_effects():
    specs = [
        {
            "x": "X",
            "y": "Y",
            "mediators": ["M1"],
            "sequence": ["X", "M1", "Y"],
            "label": "X → M1 → Y",
            "path_key": "X->M1->Y",
            "xy_key": "X->Y",
            "effect_type": "specific_indirect",
        },
        {
            "x": "X",
            "y": "Y",
            "mediators": ["M2"],
            "sequence": ["X", "M2", "Y"],
            "label": "X → M2 → Y",
            "path_key": "X->M2->Y",
            "xy_key": "X->Y",
            "effect_type": "specific_indirect",
        },
    ]
    point_by_path = {
        "X->M1->Y": 0.12,
        "X->M2->Y": 0.08,
    }
    boot_values = {
        "X->M1->Y": [0.10, 0.12, 0.13, 0.11, 0.09, 0.12, 0.14, 0.15, 0.13, 0.11, 0.12, 0.13, 0.10, 0.09, 0.11, 0.12, 0.13, 0.14, 0.15, 0.11],
        "X->M2->Y": [0.07, 0.08, 0.09, 0.06, 0.05, 0.08, 0.07, 0.09, 0.08, 0.07, 0.08, 0.09, 0.06, 0.05, 0.07, 0.08, 0.09, 0.10, 0.08, 0.07],
    }

    rows = _build_total_indirect_rows(specs, point_by_path, boot_values, 0.95)

    assert len(rows) == 1
    assert rows[0]["effect_type"] == "total_indirect"
    assert rows[0]["indirect_point"] == 0.2
    assert rows[0]["component_paths"] == ["X → M1 → Y", "X → M2 → Y"]
    assert rows[0]["ci"]["n_boot_valid"] == 20


def test_augment_lavaan_syntax_with_covariates_appends_to_existing_regressions():
    syntax = "\n".join(
        [
            "F1 =~ x1 + x2 + x3",
            "M1 ~ X",
            "Y ~ M1 + X",
        ]
    )
    patched = _augment_lavaan_syntax_with_covariates(
        syntax,
        outcomes=["M1", "Y"],
        covariates=["C1", "C2"],
    )
    assert "M1 ~ X + C1 + C2" in patched
    assert "Y ~ M1 + X + C1 + C2" in patched


def test_augment_lavaan_syntax_with_covariates_adds_new_regression_when_missing():
    syntax = "\n".join(
        [
            "F1 =~ x1 + x2 + x3",
            "M1 ~ X",
        ]
    )
    patched = _augment_lavaan_syntax_with_covariates(
        syntax,
        outcomes=["M1", "Y"],
        covariates=["C1"],
    )
    assert "M1 ~ X + C1" in patched
    assert "Y ~ C1" in patched


def test_augment_lavaan_syntax_with_covariates_dedupes_terms():
    syntax = "Y ~ X + C1"
    patched = _augment_lavaan_syntax_with_covariates(
        syntax,
        outcomes=["Y"],
        covariates=["C1", "C2"],
    )
    assert "Y ~ X + C1 + C2" in patched


def test_parse_sequence_text_accepts_arrows_and_commas():
    assert _parse_sequence_text("X, M1, M2, Y") == ["X", "M1", "M2", "Y"]
    assert _parse_sequence_text("X M1 Y") == ["X", "M1", "Y"]


def test_normalize_effect_spec_accepts_path_sequence_text():
    spec = _normalize_effect_spec({"sequence_text": "X -> M -> Y"})
    assert spec is not None
    assert spec["sequence"] == ["X", "M", "Y"]
    assert spec["label"] == "X → M → Y"


def test_normalize_effect_spec_rejects_expression_like_sequence_text():
    with pytest.raises(ValueError, match="仅支持路径序列自定义效应"):
        _normalize_effect_spec({"sequence_text": "X + M -> Y"})


def test_validate_effect_specs_allowlist_accepts_nodes_from_syntax():
    spec = _normalize_effect_spec({"x": "X", "m": "M", "y": "Y"})
    assert spec is not None
    _validate_effect_specs_allowlist(
        [spec],
        lavaan_syntax="M ~ X\nY ~ M",
        data_columns=["x1", "x2"],
    )


def test_validate_effect_specs_allowlist_rejects_unknown_node():
    spec = _normalize_effect_spec({"x": "Zbad", "m": "M", "y": "Y"})
    assert spec is not None
    with pytest.raises(ValueError, match="未出现在"):
        _validate_effect_specs_allowlist(
            [spec],
            lavaan_syntax="M ~ X\nY ~ M",
            data_columns=["x1", "x2"],
        )
