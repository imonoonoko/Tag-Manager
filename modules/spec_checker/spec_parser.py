"""
spec_parser.py
技術仕様書(MD)から関数・ファイルパス情報を抽出するモジュール
"""

from pathlib import Path
from typing import Dict, Set
import re
import logging

log_path = Path(__file__).parent.parent.parent / 'logs' / 'spec_checker.log'
logging.basicConfig(filename=log_path, level=logging.ERROR, format='%(asctime)s %(levelname)s %(message)s')

class SpecParser:
    def extract_functions_from_spec(self, spec_file: Path) -> Dict[str, Set[str]]:
        """技術仕様書から関数名を抽出"""
        spec_functions = {}
        try:
            with open(spec_file, 'r', encoding='utf-8') as f:
                content = f.read()
            current_module = None
            for line in content.split('\n'):
                if line.startswith('## ') and 'modules/' in line:
                    match = re.search(r'modules/(\w+)\.py', line)
                    if match:
                        current_module = match.group(1)
                        spec_functions[current_module] = set()
                elif line.startswith('- `') and current_module:
                    match = re.search(r'- `([^`]+)`', line)
                    if match:
                        func_name = match.group(1)
                        spec_functions[current_module].add(func_name)
        except Exception as e:
            logging.error(f"extract_functions_from_spec({spec_file}): {e}", exc_info=True)
        return spec_functions 