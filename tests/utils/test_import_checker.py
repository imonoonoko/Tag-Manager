from pathlib import Path
from modules.spec_checker.import_checker import ImportChecker

def test_check_imports(tmp_path):
    code = """
import os
from . import foo
from .bar import baz
"""
    # modulesディレクトリを作成
    modules_dir = tmp_path / "modules"
    modules_dir.mkdir()
    file = modules_dir / "sample.py"
    file.write_text(code, encoding="utf-8")
    checker = ImportChecker()
    warnings = checker.check_imports(modules_dir)
    assert any("相対インポート" in w for w in warnings) 