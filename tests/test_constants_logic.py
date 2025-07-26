import pytest
import tempfile
import os
import json
from modules.constants import safe_load_json, auto_assign_category_pure

def test_safe_load_json_success_and_fail():
    # 正常なJSON
    with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8') as f:
        json.dump({"a": 1}, f, ensure_ascii=False)
        fname = f.name
    assert safe_load_json(fname) == {"a": 1}
    os.remove(fname)
    # 存在しないファイル
    assert safe_load_json("not_exist.json") is None
    # 不正なJSON
    with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8') as f:
        f.write("{invalid json}")
        fname = f.name
    assert safe_load_json(fname) is None
    os.remove(fname)
    # ディレクトリ指定
    with tempfile.TemporaryDirectory() as d:
        assert safe_load_json(d) is None
    # パーミッションエラー（Windowsでは再現困難な場合あり、スキップ可）
    # with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8') as f:
    #     fname = f.name
    # os.chmod(fname, 0o000)
    # try:
    #     assert safe_load_json(fname) is None
    # finally:
    #     os.chmod(fname, 0o666)
    #     os.remove(fname)

def test_safe_load_json_permission_error(monkeypatch):
    """openでPermissionErrorが発生した場合にNoneが返ることを検証"""
    from modules.constants import safe_load_json
    def raise_permission_error(*a, **kw):
        raise PermissionError("no permission")
    monkeypatch.setattr("builtins.open", raise_permission_error)
    assert safe_load_json("dummy.json") is None

def test_safe_load_json_os_error(monkeypatch):
    """openでOSErrorが発生した場合にNoneが返ることを検証"""
    from modules.constants import safe_load_json
    def raise_os_error(*a, **kw):
        raise OSError("disk full")
    monkeypatch.setattr("builtins.open", raise_os_error)
    assert safe_load_json("dummy.json") is None

def test_safe_load_json_encoding_error(tmp_path):
    """エンコーディングエラー時にNoneが返ることを検証"""
    from modules.constants import safe_load_json
    # バイナリファイルを作成
    file_path = tmp_path / "binary.json"
    file_path.write_bytes(b'\x00\x01\x02\x03')
    assert safe_load_json(str(file_path)) is None

def test_safe_load_json_json_decode_error(tmp_path):
    """JSONデコードエラー時にNoneが返ることを検証"""
    from modules.constants import safe_load_json
    # 不正なJSONファイルを作成
    file_path = tmp_path / "invalid.json"
    file_path.write_text("{invalid json content", encoding="utf-8")
    assert safe_load_json(str(file_path)) is None

def test_safe_load_json_empty_file(tmp_path):
    """空ファイルの場合にNoneが返ることを検証"""
    from modules.constants import safe_load_json
    file_path = tmp_path / "empty.json"
    file_path.write_text("", encoding="utf-8")
    assert safe_load_json(str(file_path)) is None

def test_safe_load_json_directory_path(tmp_path):
    """ディレクトリパスを指定した場合にNoneが返ることを検証"""
    from modules.constants import safe_load_json
    assert safe_load_json(str(tmp_path)) is None

def test_safe_load_json_nonexistent_file():
    """存在しないファイルの場合にNoneが返ることを検証"""
    from modules.constants import safe_load_json
    assert safe_load_json("nonexistent_file.json") is None

def test_auto_assign_category_pure():
    keywords = {"A": ["foo", "bar"], "B": ["baz"]}
    priorities = {"A": 1, "B": 2}
    assert auto_assign_category_pure("foo123", keywords, priorities) == "A"
    assert auto_assign_category_pure("baz", keywords, priorities) == "B"
    assert auto_assign_category_pure("none", keywords, priorities) == "未分類"
    # 優先度が低い方が選ばれる
    keywords2 = {"A": ["foo"], "B": ["foo"]}
    priorities2 = {"A": 2, "B": 1}
    assert auto_assign_category_pure("foo", keywords2, priorities2) == "B"
    # --- 異常系 ---
    # 空辞書
    assert auto_assign_category_pure("foo", {}, {}) == "未分類"
    # None渡し
    assert auto_assign_category_pure("foo", None, None) == "未分類"
    # tagがNone
    assert auto_assign_category_pure(None, keywords, priorities) == "未分類"
    # tagが空文字
    assert auto_assign_category_pure("", keywords, priorities) == "未分類"
    # category_keywordsが不正値
    assert auto_assign_category_pure("foo", {"A": None}, {}) == "未分類" 