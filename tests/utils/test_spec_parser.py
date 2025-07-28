from pathlib import Path
from modules.spec_checker.spec_parser import SpecParser

def test_extract_functions_from_spec(tmp_path):
    md = '''
## modules/sample.py
- `foo`
- `Bar`
- `Bar.baz`
'''
    file = tmp_path / "spec.md"
    file.write_text(md, encoding="utf-8")
    parser = SpecParser()
    result = parser.extract_functions_from_spec(file)
    assert "foo" in result["sample"]
    assert "Bar" in result["sample"]
    assert "Bar.baz" in result["sample"] 