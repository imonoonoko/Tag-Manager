"""
filepath_checker.py
仕様書記載ファイルパスと実ファイルの整合性チェック
"""

from pathlib import Path
from typing import Set
import re
import logging

log_path = Path(__file__).parent.parent.parent / 'logs' / 'spec_checker.log'
logging.basicConfig(filename=log_path, level=logging.ERROR, format='%(asctime)s %(levelname)s %(message)s')

class FilePathChecker:
    def extract_paths_from_spec(self, spec_file: Path) -> Set[str]:
        """仕様書からファイルパスを抽出"""
        spec_paths = set()
        try:
            with open(spec_file, 'r', encoding='utf-8') as f:
                content = f.read()
            path_patterns = [
                r'`([^`]+\.py)`',
                r'`([^`]+\.json)`',
                r'`([^`]+\.db)`',
                r'`([^`]+\.md)`'
            ]
            for pattern in path_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if not match.startswith('http'):
                        spec_paths.add(match)
        except Exception as e:
            logging.error(f"extract_paths_from_spec({spec_file}): {e}", exc_info=True)
        return spec_paths

    def check_file_paths(self, project_root: Path, spec_paths: Set[str]) -> Set[str]:
        """仕様書記載ファイルパスの存在チェック。存在しないものを返す"""
        missing = set()
        try:
            for path_str in spec_paths:
                file_path = project_root / path_str
                if not file_path.exists():
                    missing.add(path_str)
        except Exception as e:
            logging.error(f"check_file_paths: {e}", exc_info=True)
        return missing 