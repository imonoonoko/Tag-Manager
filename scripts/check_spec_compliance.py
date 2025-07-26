#!/usr/bin/env python3
"""
技術仕様書との整合性を自動チェックするスクリプト
"""

import os
import re
import sys
import ast
from pathlib import Path
from typing import List, Dict, Set, Tuple

class SpecComplianceChecker:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.spec_file = self.project_root / "技術仕様書_関数・ファイルパス一覧.md"
        self.ai_guide_file = self.project_root / "AI_REFERENCE_GUIDE.md"
        self.todo_file = self.project_root / "ToDoリスト.md"
        
        # 重要なファイルパス
        self.important_files = [
            "modules/ui_main.py",
            "modules/tag_manager.py", 
            "modules/dialogs.py",
            "modules/theme_manager.py",
            "modules/constants.py"
        ]
        
        # 重要なクラス名
        self.important_classes = {
            "TagManager",
            "TagManagerApp", 
            "BulkCategoryDialog",
            "ThemeManager",
            "ProgressDialog",
            "ToolTip"
        }
        
        # 重要な関数名（例）
        self.important_functions = {
            "get_all_tags",
            "add_tag",
            "delete_tag",
            "update_tag",
            "refresh_tabs",
            "bulk_category_change"
        }

    def check_required_files_exist(self) -> bool:
        """必須ファイルの存在確認"""
        print("📋 必須ファイルの存在確認...")
        
        required_files = [
            self.spec_file,
            self.ai_guide_file,
            self.todo_file
        ]
        
        all_exist = True
        for file_path in required_files:
            if file_path.exists():
                print(f"✅ {file_path.name}")
            else:
                print(f"❌ {file_path.name} が見つかりません")
                all_exist = False
        
        return all_exist

    def extract_functions_from_python_file(self, file_path: Path) -> Dict[str, List[str]]:
        """Pythonファイルから関数とクラスを抽出"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            functions = []
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
            
            return {
                'functions': functions,
                'classes': classes
            }
        except Exception as e:
            print(f"⚠️  {file_path} の解析中にエラー: {e}")
            return {'functions': [], 'classes': []}

    def check_spec_file_mentions(self, file_path: Path) -> bool:
        """技術仕様書に関数・クラスが記載されているかチェック"""
        if not self.spec_file.exists():
            return False
        
        try:
            with open(self.spec_file, 'r', encoding='utf-8') as f:
                spec_content = f.read()
            
            code_info = self.extract_functions_from_python_file(file_path)
            
            missing_items = []
            
            # クラスのチェック
            for class_name in code_info['classes']:
                if class_name not in spec_content:
                    missing_items.append(f"クラス: {class_name}")
            
            # 重要な関数のチェック
            for func_name in code_info['functions']:
                if func_name in self.important_functions and func_name not in spec_content:
                    missing_items.append(f"関数: {func_name}")
            
            if missing_items:
                print(f"⚠️  {file_path.name} で技術仕様書に記載されていない項目:")
                for item in missing_items:
                    print(f"    - {item}")
                return False
            
            return True
            
        except Exception as e:
            print(f"⚠️  技術仕様書のチェック中にエラー: {e}")
            return False

    def check_file_paths(self) -> bool:
        """重要なファイルパスの存在確認"""
        print("📁 重要なファイルパスの確認...")
        
        all_exist = True
        for file_path in self.important_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                print(f"✅ {file_path}")
            else:
                print(f"❌ {file_path} が見つかりません")
                all_exist = False
        
        return all_exist

    def check_absolute_paths(self) -> bool:
        """絶対パスの使用確認"""
        print("🔍 絶対パスの使用確認...")
        
        issues_found = False
        
        for file_path in self.important_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 相対パスの使用をチェック
                relative_path_patterns = [
                    r"'resources/tags\.db'",
                    r"'resources/",
                    r"'\.\./resources/",
                    r"'config/",
                    r"'logs/"
                ]
                
                for pattern in relative_path_patterns:
                    if re.search(pattern, content):
                        print(f"⚠️  {file_path} で相対パスが使用されています: {pattern}")
                        issues_found = True
                
            except Exception as e:
                print(f"⚠️  {file_path} の確認中にエラー: {e}")
        
        return not issues_found

    def run_all_checks(self) -> bool:
        """すべてのチェックを実行"""
        print("🚀 技術仕様書との整合性チェックを開始...")
        print("=" * 50)
        
        all_passed = True
        
        # 1. 必須ファイルの存在確認
        if not self.check_required_files_exist():
            all_passed = False
        
        print()
        
        # 2. 重要なファイルパスの確認
        if not self.check_file_paths():
            all_passed = False
        
        print()
        
        # 3. 絶対パスの使用確認
        if not self.check_absolute_paths():
            all_passed = False
        
        print()
        
        # 4. 各Pythonファイルの技術仕様書との整合性確認
        print("📝 技術仕様書との整合性確認...")
        for file_path in self.important_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                if self.check_spec_file_mentions(full_path):
                    print(f"✅ {file_path}")
                else:
                    print(f"⚠️  {file_path} - 技術仕様書の更新が必要")
                    all_passed = False
        
        print()
        print("=" * 50)
        
        if all_passed:
            print("🎉 すべてのチェックが完了しました！")
            return True
        else:
            print("❌ いくつかの問題が見つかりました")
            print("技術仕様書とAI_REFERENCE_GUIDE.mdを確認してください")
            return False

def main():
    """メイン関数"""
    checker = SpecComplianceChecker()
    
    if not checker.run_all_checks():
        sys.exit(1)
    
    print("✅ 技術仕様書との整合性チェック完了")

if __name__ == "__main__":
    main() 