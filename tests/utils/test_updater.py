from pathlib import Path
from modules.spec_checker.updater import SpecUpdater

def test_suggest_spec_update(tmp_path):
    compare_result = {"mod": {"missing": {"foo"}, "undocumented": {"bar"}}}
    updater = SpecUpdater()
    dummy_spec = tmp_path / "dummy.md"
    dummy_spec.write_text("", encoding="utf-8")
    suggestion = updater.suggest_spec_update(dummy_spec, compare_result)
    assert "追加案" in suggestion
    assert "未実装" in suggestion 