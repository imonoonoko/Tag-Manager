import pytest
from pathlib import Path
from modules.spec_checker.extractor import CodeExtractor

def test_extract_functions_from_python_file(tmp_path):
    code = '''
def foo(): pass
class Bar:
    def baz(self): pass
'''
    file = tmp_path / "sample.py"
    file.write_text(code, encoding="utf-8")
    extractor = CodeExtractor()
    result = extractor.extract_functions_from_python_file(file)
    assert "foo" in result
    assert "Bar" in result
    assert "Bar.baz" in result 