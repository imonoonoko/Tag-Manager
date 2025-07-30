"""
updater.py
仕様書自動更新案生成モジュール
"""

from typing import Dict, Set
from pathlib import Path
import logging

log_path = Path(__file__).parent.parent.parent / 'logs' / 'spec_checker.log'
logging.basicConfig(filename=log_path, level=logging.ERROR, format='%(asctime)s %(levelname)s %(message)s')

class SpecUpdater:
    def suggest_spec_update(self, spec_file: Path, compare_result: Dict[str, Dict[str, Set[str]]]) -> str:
        try:
            suggestions = []
            for module, diff in compare_result.items():
                if diff['undocumented']:
                    suggestions.append(f"[追加案] {module}.py に以下の関数を仕様書へ追記: {diff['undocumented']}")
                if diff['missing']:
                    suggestions.append(f"[注意] {module}.py で未実装の関数: {diff['missing']}")
            return '\n'.join(suggestions)
        except Exception as e:
            logging.error(f"suggest_spec_update: {e}", exc_info=True)
            return "[エラー] 仕様書自動更新案生成中に例外が発生しました" 