"""
comparator.py
仕様書と実装の突合・差分検出モジュール
"""

from typing import Dict, Set
import logging
from pathlib import Path

log_path = Path(__file__).parent.parent.parent / 'logs' / 'spec_checker.log'
logging.basicConfig(filename=log_path, level=logging.ERROR, format='%(asctime)s %(levelname)s %(message)s')

class SpecComparator:
    def compare_functions(self, spec_functions: Dict[str, Set[str]], actual_functions: Dict[str, Set[str]]):
        """仕様書と実装の関数名を比較し、差分を返す"""
        try:
            results = {}
            for module, spec_funcs in spec_functions.items():
                actual_funcs = actual_functions.get(module, set())
                missing = spec_funcs - actual_funcs
                undocumented = actual_funcs - spec_funcs
                results[module] = {
                    'missing': missing,
                    'undocumented': undocumented
                }
            return results
        except Exception as e:
            logging.error(f"compare_functions: {e}", exc_info=True)
            return {} 