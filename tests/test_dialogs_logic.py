import pytest
from modules.dialogs import get_category_choices, validate_bulk_category_action
import logging
from modules.dialogs import BulkCategoryDialog
from modules.dialogs import safe_validate_bulk_category_action

def test_get_category_choices():
    keywords = {"A": [], "B": []}
    choices = get_category_choices(keywords)
    assert "A" in choices
    assert "B" in choices
    assert "未分類" in choices
    assert len(choices) == 3

def test_get_category_choices_empty():
    # 空dictの場合
    choices = get_category_choices({})
    assert choices == ["未分類"]

def test_get_category_choices_none():
    # Noneを渡した場合（AttributeErrorになる想定）
    with pytest.raises(AttributeError):
        get_category_choices(None)

def test_get_category_choices_abnormal():
    # None渡し
    with pytest.raises(AttributeError):
        get_category_choices(None)
    # 型不正
    with pytest.raises(AttributeError):
        get_category_choices(123)
    # 空dict
    assert get_category_choices({}) == ["未分類"]
    # 長すぎ
    long_key = "a"*100
    d = {long_key: []}
    choices = get_category_choices(d)
    assert long_key in choices
    # 禁止文字
    d2 = {"cat/1": []}
    choices2 = get_category_choices(d2)
    assert "cat/1" in choices2

def test_validate_bulk_category_action():
    # 正常系
    assert validate_bulk_category_action("change", "A")
    assert validate_bulk_category_action("remove", "")
    # 異常系
    assert not validate_bulk_category_action("change", "")
    # 追加: 不正action値
    assert validate_bulk_category_action("unknown", "A")
    # 追加: to_categoryがNone
    assert not validate_bulk_category_action("change", None)

def test_validate_bulk_category_action_abnormal():
    # 不正action値
    assert validate_bulk_category_action("", "A")
    assert validate_bulk_category_action(None, "A")
    # to_category None/空
    assert not validate_bulk_category_action("change", None)
    assert not validate_bulk_category_action("change", "")
    # 長すぎ
    long_cat = "a"*100
    assert validate_bulk_category_action("change", long_cat)
    # 禁止文字
    assert validate_bulk_category_action("change", "cat/1")

def test_safe_validate_bulk_category_action_logs_error(monkeypatch, caplog):
    import modules.dialogs as dialogs_mod
    import logging
    # 通常はTrue
    with caplog.at_level(logging.ERROR):
        result = dialogs_mod.safe_validate_bulk_category_action("change", "A", logger=logging.getLogger(__name__))
        assert result is True
    # 例外発生時
    def raise_error(*a, **kw):
        raise Exception("dummy error")
    monkeypatch.setattr(dialogs_mod, "validate_bulk_category_action", raise_error)
    with caplog.at_level(logging.ERROR):
        result2 = dialogs_mod.safe_validate_bulk_category_action("change", "A", logger=logging.getLogger(__name__))
        assert result2 is False
        assert any("ERROR" in r or "バリデーション例外" in r for r in caplog.text.splitlines()) 

def test_safe_validate_bulk_category_action_no_logger(monkeypatch):
    # logger無しで例外発生時もFalseを返す
    import modules.dialogs as dialogs_mod
    def raise_error(*a, **kw):
        raise Exception("dummy error")
    monkeypatch.setattr(dialogs_mod, "validate_bulk_category_action", raise_error)
    result = dialogs_mod.safe_validate_bulk_category_action("change", "A")
    assert result is False 

def test_safe_validate_bulk_category_action_abnormal(monkeypatch, caplog):
    import modules.dialogs as dialogs_mod
    # validate_bulk_category_actionが例外を投げる場合
    def raise_error(*a, **kw):
        raise Exception("dummy error")
    monkeypatch.setattr(dialogs_mod, "validate_bulk_category_action", raise_error)
    with caplog.at_level("ERROR"):
        result = dialogs_mod.safe_validate_bulk_category_action("change", "A", logger=logging.getLogger(__name__))
        assert result is False
        assert any("バリデーション例外" in r or "ERROR" in r for r in caplog.text.splitlines()) 