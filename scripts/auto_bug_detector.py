#!/usr/bin/env python3
"""
自動バグ検出システム
アプリケーションの起動、基本機能テスト、エラー検出を自動化
"""

import os
import sys
import subprocess
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import tkinter as tk
from tkinter import messagebox
import threading
import queue

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/auto_bug_detector.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class AutoBugDetector:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.bug_report = {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.28",
            "tests": [],
            "errors": [],
            "warnings": [],
            "summary": {}
        }
        self.test_queue = queue.Queue()
        self.root = None
        
    def run_full_test_suite(self) -> Dict[str, Any]:
        """完全なテストスイートを実行"""
        self.logger.info("=== 自動バグ検出システム開始 ===")
        
        try:
            # 1. 環境チェック
            self.test_environment()
            
            # 2. アプリケーション起動テスト
            self.test_app_launch()
            
            # 3. 基本機能テスト
            self.test_basic_functions()
            
            # 4. UI機能テスト
            self.test_ui_functions()
            
            # 5. データ永続化テスト
            self.test_data_persistence()
            
            # 6. エラーハンドリングテスト
            self.test_error_handling()
            
            # 7. パフォーマンステスト
            self.test_performance()
            
        except Exception as e:
            self.logger.error(f"テストスイート実行中にエラー: {e}")
            self.bug_report["errors"].append({
                "type": "test_suite_error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            })
        
        # 結果サマリー生成
        self.generate_summary()
        
        # レポート保存
        self.save_report()
        
        return self.bug_report
    
    def test_environment(self):
        """環境チェック"""
        self.logger.info("環境チェック開始...")
        
        # Python環境チェック
        python_version = sys.version_info
        if python_version.major != 3 or python_version.minor < 8:
            self.bug_report["warnings"].append({
                "type": "python_version",
                "message": f"Python 3.8以上推奨 (現在: {python_version.major}.{python_version.minor})"
            })
        
        # 必要なファイルチェック
        required_files = [
            "main.py",
            "modules/ui_main.py",
            "modules/tag_manager.py",
            "resources/config/categories.json"
        ]
        
        for file_path in required_files:
            if not os.path.exists(file_path):
                self.bug_report["errors"].append({
                    "type": "missing_file",
                    "file": file_path,
                    "message": f"必要なファイルが見つかりません: {file_path}"
                })
        
        self.bug_report["tests"].append({
            "name": "環境チェック",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        })
    
    def test_app_launch(self):
        """アプリケーション起動テスト"""
        self.logger.info("アプリケーション起動テスト開始...")
        
        try:
            # アプリケーションを起動
            process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 5秒待機
            time.sleep(5)
            
            # プロセスが正常に動作しているかチェック
            if process.poll() is None:
                self.logger.info("アプリケーション正常起動")
                process.terminate()
                process.wait(timeout=5)
            else:
                stdout, stderr = process.communicate()
                self.bug_report["errors"].append({
                    "type": "app_launch_failure",
                    "stdout": stdout,
                    "stderr": stderr,
                    "message": "アプリケーションの起動に失敗しました"
                })
                
        except Exception as e:
            self.bug_report["errors"].append({
                "type": "app_launch_error",
                "message": f"起動テスト中にエラー: {e}"
            })
        
        self.bug_report["tests"].append({
            "name": "アプリケーション起動",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        })
    
    def test_basic_functions(self):
        """基本機能テスト"""
        self.logger.info("基本機能テスト開始...")
        
        try:
            # モジュールインポートテスト
            import modules.ui_main
            import modules.tag_manager
            import modules.theme_manager
            import modules.customization
            
            # クラス初期化テスト
            from modules.tag_manager import TagManager
            from modules.theme_manager import ThemeManager
            
            # テスト用DBで初期化
            test_db = "test_bug_detector.db"
            tag_manager = TagManager(test_db)
            theme_manager = ThemeManager()
            
            # 基本操作テスト
            # タグ追加テスト
            success = tag_manager.add_tag("test_tag", False, "テストカテゴリ")
            if not success:
                self.bug_report["errors"].append({
                    "type": "tag_add_failure",
                    "message": "タグ追加機能に問題があります"
                })
            
            # タグ存在チェック
            if not tag_manager.exists_tag("test_tag"):
                self.bug_report["errors"].append({
                    "type": "tag_exists_check_failure",
                    "message": "タグ存在チェック機能に問題があります"
                })
            
            # クリーンアップ
            tag_manager.close()
            if os.path.exists(test_db):
                os.remove(test_db)
                
        except Exception as e:
            self.bug_report["errors"].append({
                "type": "basic_functions_error",
                "message": f"基本機能テスト中にエラー: {e}"
            })
        
        self.bug_report["tests"].append({
            "name": "基本機能テスト",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        })
    
    def test_ui_functions(self):
        """UI機能テスト"""
        self.logger.info("UI機能テスト開始...")
        
        try:
            # Tkinter環境チェック
            root = tk.Tk()
            root.withdraw()  # ウィンドウを非表示
            
            # UIコンポーネント作成テスト
            from modules.ui_main import TagManagerApp
            
            app = TagManagerApp(root, "test_ui.db")
            
            # 属性存在チェック
            required_attributes = [
                'tag_manager', 'theme_manager', 'category_list',
                'current_category', 'output_tags_data', 'weight_values'
            ]
            
            for attr in required_attributes:
                if not hasattr(app, attr):
                    self.bug_report["errors"].append({
                        "type": "missing_attribute",
                        "attribute": attr,
                        "message": f"必要な属性が初期化されていません: {attr}"
                    })
            
            # メソッド存在チェック
            required_methods = [
                'save_app_settings', 'on_closing', 'add_to_output',
                'insert_weighted_tags', 'prompt_and_add_tags'
            ]
            
            for method in required_methods:
                if not hasattr(app, method):
                    self.bug_report["errors"].append({
                        "type": "missing_method",
                        "method": method,
                        "message": f"必要なメソッドが存在しません: {method}"
                    })
            
            # クリーンアップ
            app.tag_manager.close()
            root.destroy()
            
            if os.path.exists("test_ui.db"):
                os.remove("test_ui.db")
                
        except Exception as e:
            self.bug_report["errors"].append({
                "type": "ui_functions_error",
                "message": f"UI機能テスト中にエラー: {e}"
            })
        
        self.bug_report["tests"].append({
            "name": "UI機能テスト",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        })
    
    def test_data_persistence(self):
        """データ永続化テスト"""
        self.logger.info("データ永続化テスト開始...")
        
        try:
            # テーマ設定保存テスト
            from modules.theme_manager import ThemeManager
            theme_manager = ThemeManager()
            
            # テスト用テーマ設定
            test_theme = "cosmo"
            theme_manager.save_theme_settings(test_theme)
            
            # 設定読み込みテスト
            loaded_settings = theme_manager._load_theme_settings()
            if not loaded_settings or loaded_settings.get('theme') != test_theme:
                self.bug_report["errors"].append({
                    "type": "theme_persistence_failure",
                    "message": "テーマ設定の永続化に問題があります"
                })
            
            # カスタマイズ設定テスト
            from modules.customization import UserSettings
            user_settings = UserSettings()
            
            # テスト設定
            test_setting = "test_value"
            user_settings.set_setting("test_key", test_setting)
            
            # 設定読み込みテスト
            loaded_value = user_settings.get_setting("test_key")
            if loaded_value != test_setting:
                self.bug_report["errors"].append({
                    "type": "user_settings_persistence_failure",
                    "message": "ユーザー設定の永続化に問題があります"
                })
                
        except Exception as e:
            self.bug_report["errors"].append({
                "type": "data_persistence_error",
                "message": f"データ永続化テスト中にエラー: {e}"
            })
        
        self.bug_report["tests"].append({
            "name": "データ永続化テスト",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        })
    
    def test_error_handling(self):
        """エラーハンドリングテスト"""
        self.logger.info("エラーハンドリングテスト開始...")
        
        try:
            from modules.tag_manager import TagManager
            
            # 無効なタグ追加テスト
            tag_manager = TagManager("test_error.db")
            
            # 空文字列タグ
            result = tag_manager.add_tag("", False, "")
            if result:
                self.bug_report["warnings"].append({
                    "type": "empty_tag_accepted",
                    "message": "空文字列のタグが受け入れられています"
                })
            
            # 長すぎるタグ
            long_tag = "a" * 100
            result = tag_manager.add_tag(long_tag, False, "")
            if result:
                self.bug_report["warnings"].append({
                    "type": "long_tag_accepted",
                    "message": "長すぎるタグが受け入れられています"
                })
            
            tag_manager.close()
            if os.path.exists("test_error.db"):
                os.remove("test_error.db")
                
        except Exception as e:
            self.bug_report["errors"].append({
                "type": "error_handling_test_error",
                "message": f"エラーハンドリングテスト中にエラー: {e}"
            })
        
        self.bug_report["tests"].append({
            "name": "エラーハンドリングテスト",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        })
    
    def test_performance(self):
        """パフォーマンステスト"""
        self.logger.info("パフォーマンステスト開始...")
        
        try:
            from modules.tag_manager import TagManager
            import time
            
            tag_manager = TagManager("test_performance.db")
            
            # 大量タグ追加テスト
            start_time = time.time()
            for i in range(100):
                tag_manager.add_tag(f"perf_tag_{i}", False, "パフォーマンステスト")
            
            end_time = time.time()
            duration = end_time - start_time
            
            if duration > 5.0:  # 5秒以上かかる場合は警告
                self.bug_report["warnings"].append({
                    "type": "slow_tag_addition",
                    "message": f"タグ追加が遅いです: {duration:.2f}秒"
                })
            
            # 大量タグ検索テスト
            start_time = time.time()
            for i in range(100):
                tag_manager.exists_tag(f"perf_tag_{i}")
            
            end_time = time.time()
            duration = end_time - start_time
            
            if duration > 2.0:  # 2秒以上かかる場合は警告
                self.bug_report["warnings"].append({
                    "type": "slow_tag_search",
                    "message": f"タグ検索が遅いです: {duration:.2f}秒"
                })
            
            tag_manager.close()
            if os.path.exists("test_performance.db"):
                os.remove("test_performance.db")
                
        except Exception as e:
            self.bug_report["errors"].append({
                "type": "performance_test_error",
                "message": f"パフォーマンステスト中にエラー: {e}"
            })
        
        self.bug_report["tests"].append({
            "name": "パフォーマンステスト",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        })
    
    def generate_summary(self):
        """結果サマリー生成"""
        total_tests = len(self.bug_report["tests"])
        total_errors = len(self.bug_report["errors"])
        total_warnings = len(self.bug_report["warnings"])
        
        self.bug_report["summary"] = {
            "total_tests": total_tests,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "success_rate": ((total_tests - total_errors) / total_tests * 100) if total_tests > 0 else 0,
            "status": "PASS" if total_errors == 0 else "FAIL"
        }
        
        self.logger.info(f"=== テスト結果サマリー ===")
        self.logger.info(f"総テスト数: {total_tests}")
        self.logger.info(f"エラー数: {total_errors}")
        self.logger.info(f"警告数: {total_warnings}")
        self.logger.info(f"成功率: {self.bug_report['summary']['success_rate']:.1f}%")
        self.logger.info(f"ステータス: {self.bug_report['summary']['status']}")
    
    def save_report(self):
        """レポート保存"""
        try:
            os.makedirs("logs", exist_ok=True)
            
            # JSONレポート
            report_file = f"logs/bug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.bug_report, f, ensure_ascii=False, indent=2)
            
            # 簡易レポート
            summary_file = f"logs/bug_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("=== 自動バグ検出レポート ===\n")
                f.write(f"日時: {self.bug_report['timestamp']}\n")
                f.write(f"バージョン: {self.bug_report['version']}\n")
                f.write(f"ステータス: {self.bug_report['summary']['status']}\n")
                f.write(f"成功率: {self.bug_report['summary']['success_rate']:.1f}%\n\n")
                
                if self.bug_report["errors"]:
                    f.write("=== エラー ===\n")
                    for error in self.bug_report["errors"]:
                        f.write(f"- {error['type']}: {error['message']}\n")
                    f.write("\n")
                
                if self.bug_report["warnings"]:
                    f.write("=== 警告 ===\n")
                    for warning in self.bug_report["warnings"]:
                        f.write(f"- {warning['type']}: {warning['message']}\n")
            
            self.logger.info(f"レポート保存完了: {report_file}")
            self.logger.info(f"サマリー保存完了: {summary_file}")
            
        except Exception as e:
            self.logger.error(f"レポート保存中にエラー: {e}")

def main():
    """メイン実行関数"""
    detector = AutoBugDetector()
    report = detector.run_full_test_suite()
    
    # 結果表示
    if report["summary"]["status"] == "PASS":
        print("✅ すべてのテストが成功しました！")
    else:
        print("❌ エラーが検出されました。")
        print(f"エラー数: {report['summary']['total_errors']}")
        print(f"警告数: {report['summary']['total_warnings']}")
        print("詳細は logs/ フォルダのレポートを確認してください。")

if __name__ == "__main__":
    main() 