"""data_key 存储：磁盘持久化与 drop 清理。"""

import pandas as pd
import pytest

from app.services import data_parser


def test_get_data_survives_memory_clear_via_disk(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENSEM_DATA_STORE_DIR", str(tmp_path))
    monkeypatch.delenv("OPENSEM_REDIS_URL", raising=False)

    csv_bytes = b"a,b\n1,2\n3,4\n"
    out = data_parser.parse_file(csv_bytes, "t.csv", len(csv_bytes))
    key = out["data_key"]
    assert key

    df0 = data_parser.get_data(key)
    assert df0 is not None
    assert list(df0.columns) == ["a", "b"]

    data_parser._data_store.clear()

    df1 = data_parser.get_data(key)
    assert df1 is not None
    pd.testing.assert_frame_equal(df0, df1)


def test_drop_data_removes_disk_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENSEM_DATA_STORE_DIR", str(tmp_path))
    monkeypatch.delenv("OPENSEM_REDIS_URL", raising=False)

    csv_bytes = b"x\n1\n"
    out = data_parser.parse_file(csv_bytes, "t.csv", len(csv_bytes))
    key = out["data_key"]

    pkl = data_parser._disk_path(key)
    assert pkl.is_file()

    data_parser.drop_data(key)
    assert not pkl.is_file()
    assert data_parser.get_data(key) is None
