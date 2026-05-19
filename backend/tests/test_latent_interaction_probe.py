from app.tasks.stats_tasks import _latent_interaction_preconditions


def test_latent_interaction_preconditions_returns_structured_constraints():
    payload = _latent_interaction_preconditions(
        y="Y",
        f1="F1",
        f2="F2",
        estimator="ML",
        missing_strategy="listwise",
    )

    assert payload["input_constraints"]["required_fields"] == [
        "data_key",
        "lavaan_syntax",
        "y",
        "f1",
        "f2",
    ]
    assert payload["input_constraints"]["distinct_roles"]["all_distinct"] is True
    assert payload["input_constraints"]["supported_estimators"] == ["ML", "GLS"]
    assert payload["environment_boundaries"]["engine"] == "semopy"
    assert len(payload["runtime_checks"]) >= 3
