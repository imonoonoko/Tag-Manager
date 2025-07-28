#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技術仕様書との整合性チェックスクリプト
AI開発者がコード変更時に必ず実行すべきスクリプト
"""

import os
import sys
import re
import ast
from pathlib import Path
from typing import List, Dict, Set, Tuple

# プロジェクトルートをsys.pathに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.spec_checker.extractor import CodeExtractor
from modules.spec_checker.spec_parser import SpecParser
from modules.spec_checker.comparator import SpecComparator
from modules.spec_checker.reporter import ReportGenerator
from modules.spec_checker.updater import SpecUpdater
from modules.spec_checker.filepath_checker import FilePathChecker
from modules.spec_checker.import_checker import ImportChecker

class SpecComplianceChecker:
    """技術仕様書との整合性チェッククラス（新モジュール利用版）"""
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.spec_file = self.project_root / "技術仕様書_関数・ファイルパス一覧.md"
        self.modules_dir = self.project_root / "modules"
        self.extractor = CodeExtractor()
        self.spec_parser = SpecParser()
        self.comparator = SpecComparator()
        self.reporter = ReportGenerator()
        self.updater = SpecUpdater()
        self.errors = []
        self.warnings = []
        self.filepath_checker = FilePathChecker()
        self.import_checker = ImportChecker()
    def check_required_files(self) -> bool:
        """必須ファイルの存在確認"""
        print("📋 必須ファイルの存在確認...")
        required_files = [
            self.spec_file,
            self.modules_dir / "ui_main.py",
            self.modules_dir / "tag_manager.py",
            self.modules_dir / "ai_predictor.py",
            self.modules_dir / "config.py",
            self.modules_dir / "constants.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not file_path.exists():
                missing_files.append(str(file_path))
        
        if missing_files:
            self.errors.append(f"❌ 必須ファイルが存在しません: {missing_files}")
            return False
        
        return True
    
    def check_function_consistency(self) -> bool:
        """関数名の整合性チェック（新モジュール利用）"""
        print("🔍 関数名の整合性チェック...")
        spec_functions = self.spec_parser.extract_functions_from_spec(self.spec_file)
        actual_functions = {}
        for module_name in spec_functions.keys():
            module_file = self.modules_dir / f"{module_name}.py"
            if not module_file.exists():
                self.warnings.append(f"⚠️  {module_file.name} が存在しません")
                continue
            actual_functions[module_name] = self.extractor.extract_functions_from_python_file(module_file)
        compare_result = self.comparator.compare_functions(spec_functions, actual_functions)
        report = self.reporter.generate_function_report(compare_result)
        if report:
            self.warnings.append(report)
        update_suggestion = self.updater.suggest_spec_update(self.spec_file, compare_result)
        if update_suggestion:
            self.warnings.append(update_suggestion)
        # missingがあればall_consistent=False
        all_consistent = all(not v['missing'] for v in compare_result.values())
        return all_consistent
    
    def check_file_paths(self) -> bool:
        """ファイルパスの整合性チェック（新モジュール利用）"""
        print("📁 ファイルパスの整合性チェック...")
        spec_paths = self.filepath_checker.extract_paths_from_spec(self.spec_file)
        missing = self.filepath_checker.check_file_paths(self.project_root, spec_paths)
        if missing:
            self.warnings.append(f"⚠️  技術仕様書に記載されているが存在しないファイル: {missing}")
        return not missing
    
    def check_imports(self) -> bool:
        """インポート文の整合性チェック（新モジュール利用）"""
        print("📦 インポート文の整合性チェック...")
        warnings = self.import_checker.check_imports(self.modules_dir)
        if warnings:
            self.warnings.extend(warnings)
        return True
    
    def run_all_checks(self) -> bool:
        """すべてのチェックを実行"""
        print("🚀 技術仕様書との整合性チェックを開始...")
        print("=" * 50)
        
        checks = [
            ("必須ファイル確認", self.check_required_files),
            ("関数名整合性", self.check_function_consistency),
            ("ファイルパス整合性", self.check_file_paths),
            ("インポート文整合性", self.check_imports)
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            print(f"\n🔍 {check_name}...")
            try:
                result = check_func()
                if not result:
                    all_passed = False
            except Exception as e:
                self.errors.append(f"❌ {check_name}中にエラー: {e}")
                all_passed = False
                
        return all_passed
    
    def print_results(self):
        """結果を表示"""
        print("\n" + "=" * 50)
        print("📊 チェック結果")
        print("=" * 50)
        
        if self.errors:
            print("\n❌ エラー:")
            for error in self.errors:
                print(f"  {error}")
                
        if self.warnings:
            print("\n⚠️  警告:")
            for warning in self.warnings:
                print(f"  {warning}")
                
        if not self.errors and not self.warnings:
            print("\n🎉 すべてのチェックが完了しました！")
            print("技術仕様書との整合性が確認されました")
        elif not self.errors:
            print("\n⚠️  警告がありますが、エラーはありません")
        else:
            print("\n❌ エラーがあります。修正してから再実行してください")
            
        return len(self.errors) == 0

def main():
    """メイン関数"""
    checker = SpecComplianceChecker()
    
    try:
        success = checker.run_all_checks()
        final_success = checker.print_results()
        
        if not final_success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  チェックが中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 