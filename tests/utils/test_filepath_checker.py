from pathlib import Path
from modules.spec_checker.filepath_checker import FilePathChecker

def test_extract_paths_from_spec(tmp_path):
    md = '''
- `modules/sample.py`
- `data/sample.json`
'''
    file = tmp_path / "spec.md"
    file.write_text(md, encoding="utf-8")
    checker = FilePathChecker()
    paths = checker.extract_paths_from_spec(file)
    assert "modules/sample.py" in paths
    assert "data/sample.json" in paths

def test_check_file_paths(tmp_path):
    (tmp_path / "modules").mkdir()
    (tmp_path / "modules/sample.py").write_text("", encoding="utf-8")
    checker = FilePathChecker()
    missing = checker.check_file_paths(tmp_path, {"modules/sample.py", "notfound.py"})
    assert "notfound.py" in missing
    assert "modules/sample.py" not in missing 