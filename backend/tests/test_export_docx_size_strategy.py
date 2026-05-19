def test_truncate_docx_rows_keeps_prefix_and_reports_omitted():
    from app.api.v1.export import _truncate_docx_rows

    rows = [{"i": i} for i in range(15)]
    kept, omitted = _truncate_docx_rows(rows, limit=10)

    assert len(kept) == 10
    assert kept[0]["i"] == 0
    assert kept[-1]["i"] == 9
    assert omitted == 5


def test_truncate_docx_rows_no_truncation_when_within_limit():
    from app.api.v1.export import _truncate_docx_rows

    rows = [{"i": i} for i in range(3)]
    kept, omitted = _truncate_docx_rows(rows, limit=10)

    assert len(kept) == 3
    assert omitted == 0
