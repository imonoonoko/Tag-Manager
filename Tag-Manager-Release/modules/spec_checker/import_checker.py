"""
import_checker.py
インポート文の整合性チェック
"""

from pathlib import Path
from typing import List
import ast
import logging

log_path = Path(__file__).parent.parent.parent / 'logs' / 'spec_checker.log'
logging.basicConfig(filename=log_path, level=logging.ERROR, format='%(asctime)s %(levelname)s %(message)s')

class ImportChecker:
    def check_imports(self, modules_dir: Path) -> List[str]:
        """相対インポートの有無などをチェックし、警告リストを返す"""
        warnings = []
        try:
            for py_file in modules_dir.glob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                if alias.name.startswith('.'):
                                    warnings.append(f"[警告] {py_file.name} で相対インポート: {alias.name}")
                        elif isinstance(node, ast.ImportFrom):
                            if node.module and node.module.startswith('.'):
                                warnings.append(f"[警告] {py_file.name} で相対インポート: {node.module}")
                            # レベルが0より大きい場合も相対インポート
                            elif hasattr(node, 'level') and node.level > 0:
                                module_name = node.module or ''
                                warnings.append(f"[警告] {py_file.name} で相対インポート: {'.' * node.level}{module_name}")
                except Exception as e:
                    logging.error(f"check_imports({py_file}): {e}", exc_info=True)
        except Exception as e:
            logging.error(f"check_imports(modules_dir): {e}", exc_info=True)
        return warnings 