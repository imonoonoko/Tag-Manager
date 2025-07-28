"""
extractor.py
コードベースから関数・クラス・ファイルパスを抽出するモジュール
"""

from pathlib import Path
from typing import Set, Dict
import ast
import logging

log_path = Path(__file__).parent.parent.parent / 'logs' / 'spec_checker.log'
logging.basicConfig(filename=log_path, level=logging.ERROR, format='%(asctime)s %(levelname)s %(message)s')

class CodeExtractor:
    def extract_functions_from_python_file(self, file_path: Path) -> Set[str]:
        """Pythonファイルから関数・クラス名を抽出"""
        functions = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.add(node.name)
                elif isinstance(node, ast.ClassDef):
                    functions.add(node.name)
                    for class_node in ast.walk(node):
                        if isinstance(class_node, ast.FunctionDef):
                            functions.add(f"{node.name}.{class_node.name}")
        except Exception as e:
            logging.error(f"extract_functions_from_python_file({file_path}): {e}", exc_info=True)
        return functions 