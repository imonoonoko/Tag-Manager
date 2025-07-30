"""
reporter.py
差分や警告のレポート生成モジュール
"""

from typing import Dict, Set
import logging
from pathlib import Path

log_path = Path(__file__).parent.parent.parent / 'logs' / 'spec_checker.log'
logging.basicConfig(filename=log_path, level=logging.ERROR, format='%(asctime)s %(levelname)s %(message)s')

class ReportGenerator:
    def generate_function_report(self, compare_result: Dict[str, Dict[str, Set[str]]]) -> str:
        """関数名の差分レポートを生成"""
        try:
            report = []
            for module, diff in compare_result.items():
                if diff['missing']:
                    report.append(f"[警告] {module}.py: 未実装関数: {diff['missing']}")
                if diff['undocumented']:
                    report.append(f"[警告] {module}.py: 仕様書未記載関数: {diff['undocumented']}")
            return '\n'.join(report)
        except Exception as e:
            logging.error(f"generate_function_report: {e}", exc_info=True)
            return "[エラー] レポート生成中に例外が発生しました" 