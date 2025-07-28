#!/usr/bin/env python3
"""
品質チェック実行スクリプト
包括的な品質チェックを簡単に実行できます。
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

def run_command(command, description):
    """コマンドを実行し、結果を表示"""
    print(f"\n🔍 {description}")
    print(f"実行コマンド: {command}")
    print("-" * 50)
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
        
        if result.stdout:
            print("出力:")
            print(result.stdout)
        
        if result.stderr:
            print("エラー:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ 成功")
            return True
        else:
            print(f"❌ 失敗 (終了コード: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ タイムアウト")
        return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def main():
    """メイン関数"""
    print("🚀 品質チェック実行スクリプト")
    print("=" * 60)
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # プロジェクトルートに移動
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # 必要なディレクトリを作成
    Path("logs").mkdir(exist_ok=True)
    Path("backup").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    # チェック項目
    checks = [
        {
            "command": "python scripts/check_duplicate_functions.py modules",
            "description": "重複関数定義チェック"
        },
        {
            "command": "python scripts/check_code_quality.py modules --no-mypy --no-pytest",
            "description": "包括的コード品質チェック"
        },
        {
            "command": "python scripts/check_spec_compliance.py",
            "description": "仕様書整合性チェック"
        },
        {
            "command": "python -m py_compile modules/ui_main.py",
            "description": "構文チェック (ui_main.py)"
        },
        {
            "command": "python -m py_compile modules/tag_manager.py",
            "description": "構文チェック (tag_manager.py)"
        },
        {
            "command": "python -m py_compile modules/ai_predictor.py",
            "description": "構文チェック (ai_predictor.py)"
        }
    ]
    
    # オプションのチェック項目
    optional_checks = [
        {
            "command": "mypy modules/ --strict",
            "description": "型チェック"
        },
        {
            "command": "pytest tests/ -v",
            "description": "テスト実行"
        }
    ]
    
    # 必須チェックの実行
    print("\n📋 必須チェック項目")
    print("=" * 30)
    
    all_passed = True
    for check in checks:
        if not run_command(check["command"], check["description"]):
            all_passed = False
    
    # オプションチェックの実行
    print("\n📋 オプションチェック項目")
    print("=" * 30)
    
    print("\nオプションチェックを実行しますか？ (y/n): ", end="")
    try:
        response = input().lower().strip()
        if response in ['y', 'yes', 'はい']:
            for check in optional_checks:
                run_command(check["command"], check["description"])
    except KeyboardInterrupt:
        print("\nオプションチェックをスキップしました。")
    
    # 結果の表示
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 すべての必須チェックが成功しました！")
        print("✅ コード品質は良好です。")
        sys.exit(0)
    else:
        print("❌ 一部のチェックが失敗しました。")
        print("🔧 問題を修正してから再度実行してください。")
        sys.exit(1)

if __name__ == "__main__":
    main() 