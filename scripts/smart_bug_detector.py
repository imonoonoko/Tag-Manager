#!/usr/bin/env python3
"""
スマートバグ検出システム
複数の検出方法を組み合わせて包括的なバグ検出を実行
"""

import os
import sys
import time
import json
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Any
import tkinter as tk
from tkinter import messagebox

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/smart_bug_detector.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class SmartBugDetector:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.bug_report = {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.28",
            "detection_methods": [],
            "issues": [],
            "recommendations": [],
            "summary": {}
        }
        
    def run_comprehensive_detection(self) -> Dict[str, Any]:
        """包括的なバグ検出を実行"""
        self.logger.info("=== スマートバグ検出システム開始 ===")
        
        # 1. 静的解析
        self.static_analysis()
        
        # 2. 動的テスト
        self.dynamic_testing()
        
        # 3. 設定チェック
        self.configuration_check()
        
        # 4. 依存関係チェック
        self.dependency_check()
        
        # 5. セキュリティチェック
        self.security_check()
        
        # 6. パフォーマンス分析
        self.performance_analysis()
        
        # 7. 推奨事項生成
        self.generate_recommendations()
        
        # 8. サマリー生成
        self.generate_summary()
        
        # 9. レポート保存
        self.save_report()
        
        return self.bug_report
    
    def static_analysis(self):
        """静的解析"""
        self.logger.info("静的解析開始...")
        
        # コードの構文チェック
        python_files = self.get_python_files()
        
        for file_path in python_files:
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "py_compile", file_path],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    self.add_issue("syntax_error", f"構文エラー: {file_path} - {result.stderr}")
                    
            except Exception as e:
                self.add_issue("static_analysis_error", f"静的解析エラー: {file_path} - {e}")
        
        self.bug_report["detection_methods"].append({
            "method": "static_analysis",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        })
    
    def dynamic_testing(self):
        """動的テスト"""
        self.logger.info("動的テスト開始...")
        
        try:
            # アプリケーション起動テスト
            process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 10秒待機
            time.sleep(10)
            
            if process.poll() is None:
                # 正常に動作中
                process.terminate()
                process.wait(timeout=5)
                self.logger.info("動的テスト: アプリケーション正常起動")
            else:
                stdout, stderr = process.communicate()
                if stderr:
                    self.add_issue("runtime_error", f"実行時エラー: {stderr}")
                    
        except Exception as e:
            self.add_issue("dynamic_test_error", f"動的テストエラー: {e}")
        
        self.bug_report["detection_methods"].append({
            "method": "dynamic_testing",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        })
    
    def configuration_check(self):
        """設定チェック"""
        self.logger.info("設定チェック開始...")
        
        config_files = [
            "resources/config/ai_settings.json",
            "resources/config/theme_settings.json",
            "resources/config/categories.json"
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 設定の妥当性チェック
                    if isinstance(data, dict):
                        if not data:
                            self.add_issue("empty_config", f"設定ファイルが空です: {config_file}")
                    else:
                        self.add_issue("invalid_config_format", f"設定ファイルの形式が不正です: {config_file}")
                        
                except json.JSONDecodeError as e:
                    self.add_issue("json_syntax_error", f"JSON構文エラー: {config_file} - {e}")
                except Exception as e:
                    self.add_issue("config_read_error", f"設定ファイル読み込みエラー: {config_file} - {e}")
            else:
                self.add_issue("missing_config", f"設定ファイルが見つかりません: {config_file}")
        
        self.bug_report["detection_methods"].append({
            "method": "configuration_check",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        })
    
    def dependency_check(self):
        """依存関係チェック"""
        self.logger.info("依存関係チェック開始...")
        
        required_modules = [
            "tkinter", "json", "sqlite3", "threading", "queue",
            "ttkbootstrap", "psutil", "numpy", "torch", "transformers"
        ]
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError as e:
                self.add_issue("missing_dependency", f"必要なモジュールが不足: {module} - {e}")
        
        self.bug_report["detection_methods"].append({
            "method": "dependency_check",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        })
    
    def security_check(self):
        """セキュリティチェック"""
        self.logger.info("セキュリティチェック開始...")
        
        # ファイル権限チェック
        critical_files = [
            "modules/data/tags.db",
            "resources/config/ai_settings.json"
        ]
        
        for file_path in critical_files:
            if os.path.exists(file_path):
                # ファイル権限チェック（簡易版）
                try:
                    with open(file_path, 'r') as f:
                        pass
                except PermissionError:
                    self.add_issue("permission_error", f"ファイルアクセス権限エラー: {file_path}")
        
        self.bug_report["detection_methods"].append({
            "method": "security_check",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        })
    
    def performance_analysis(self):
        """パフォーマンス分析"""
        self.logger.info("パフォーマンス分析開始...")
        
        try:
            # ファイルサイズチェック
            large_files = []
            for root, dirs, files in os.walk("."):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        size = os.path.getsize(file_path)
                        if size > 50 * 1024 * 1024:  # 50MB以上
                            large_files.append((file_path, size))
                    except:
                        pass
            
            if large_files:
                for file_path, size in large_files:
                    self.add_issue("large_file", f"大きなファイル: {file_path} ({size/1024/1024:.1f}MB)")
                    
        except Exception as e:
            self.add_issue("performance_analysis_error", f"パフォーマンス分析エラー: {e}")
        
        self.bug_report["detection_methods"].append({
            "method": "performance_analysis",
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        })
    
    def generate_recommendations(self):
        """推奨事項生成"""
        self.logger.info("推奨事項生成開始...")
        
        # エラーに基づく推奨事項
        error_types = [issue["type"] for issue in self.bug_report["issues"]]
        
        if "syntax_error" in error_types:
            self.bug_report["recommendations"].append({
                "priority": "high",
                "action": "コードの構文エラーを修正してください",
                "description": "Pythonの構文エラーが検出されました"
            })
        
        if "missing_dependency" in error_types:
            self.bug_report["recommendations"].append({
                "priority": "high",
                "action": "不足しているモジュールをインストールしてください",
                "description": "必要な依存関係が不足しています"
            })
        
        if "runtime_error" in error_types:
            self.bug_report["recommendations"].append({
                "priority": "high",
                "action": "アプリケーションの起動エラーを調査してください",
                "description": "実行時にエラーが発生しています"
            })
        
        if "large_file" in error_types:
            self.bug_report["recommendations"].append({
                "priority": "medium",
                "action": "大きなファイルの最適化を検討してください",
                "description": "パフォーマンスに影響する可能性があります"
            })
        
        # 一般的な推奨事項
        self.bug_report["recommendations"].append({
            "priority": "low",
            "action": "定期的なバックアップを実行してください",
            "description": "データの安全性を確保するため"
        })
    
    def generate_summary(self):
        """サマリー生成"""
        total_issues = len(self.bug_report["issues"])
        total_recommendations = len(self.bug_report["recommendations"])
        
        # 重要度別カウント
        high_priority = len([r for r in self.bug_report["recommendations"] if r["priority"] == "high"])
        medium_priority = len([r for r in self.bug_report["recommendations"] if r["priority"] == "medium"])
        low_priority = len([r for r in self.bug_report["recommendations"] if r["priority"] == "low"])
        
        self.bug_report["summary"] = {
            "total_issues": total_issues,
            "total_recommendations": total_recommendations,
            "high_priority_recommendations": high_priority,
            "medium_priority_recommendations": medium_priority,
            "low_priority_recommendations": low_priority,
            "status": "HEALTHY" if total_issues == 0 else "NEEDS_ATTENTION"
        }
        
        self.logger.info(f"=== 検出結果サマリー ===")
        self.logger.info(f"問題数: {total_issues}")
        self.logger.info(f"推奨事項数: {total_recommendations}")
        self.logger.info(f"高優先度: {high_priority}")
        self.logger.info(f"中優先度: {medium_priority}")
        self.logger.info(f"低優先度: {low_priority}")
        self.logger.info(f"ステータス: {self.bug_report['summary']['status']}")
    
    def save_report(self):
        """レポート保存"""
        try:
            os.makedirs("logs", exist_ok=True)
            
            # JSONレポート
            report_file = f"logs/smart_bug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.bug_report, f, ensure_ascii=False, indent=2)
            
            # 簡易レポート
            summary_file = f"logs/smart_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("=== スマートバグ検出レポート ===\n")
                f.write(f"日時: {self.bug_report['timestamp']}\n")
                f.write(f"バージョン: {self.bug_report['version']}\n")
                f.write(f"ステータス: {self.bug_report['summary']['status']}\n\n")
                
                if self.bug_report["issues"]:
                    f.write("=== 検出された問題 ===\n")
                    for issue in self.bug_report["issues"]:
                        f.write(f"- {issue['type']}: {issue['message']}\n")
                    f.write("\n")
                
                if self.bug_report["recommendations"]:
                    f.write("=== 推奨事項 ===\n")
                    for rec in self.bug_report["recommendations"]:
                        f.write(f"- [{rec['priority'].upper()}] {rec['action']}\n")
                        f.write(f"  理由: {rec['description']}\n\n")
            
            self.logger.info(f"レポート保存完了: {report_file}")
            self.logger.info(f"サマリー保存完了: {summary_file}")
            
        except Exception as e:
            self.logger.error(f"レポート保存中にエラー: {e}")
    
    def get_python_files(self) -> List[str]:
        """Pythonファイル一覧取得"""
        python_files = []
        for root, dirs, files in os.walk("."):
            # 除外ディレクトリ
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'venv', 'node_modules']]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        return python_files
    
    def add_issue(self, issue_type: str, message: str):
        """問題を記録"""
        issue = {
            "type": issue_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.bug_report["issues"].append(issue)
        self.logger.warning(f"問題検出: {issue_type} - {message}")

def main():
    """メイン実行関数"""
    detector = SmartBugDetector()
    report = detector.run_comprehensive_detection()
    
    # 結果表示
    print("\n" + "="*50)
    print("スマートバグ検出システム - 結果")
    print("="*50)
    
    if report["summary"]["status"] == "HEALTHY":
        print("✅ アプリケーションは健全です！")
    else:
        print("⚠️ 注意が必要な問題が検出されました")
        print(f"問題数: {report['summary']['total_issues']}")
        print(f"推奨事項数: {report['summary']['total_recommendations']}")
    
    print(f"\n詳細レポート: logs/smart_bug_report_*.json")
    print(f"簡易サマリー: logs/smart_summary_*.txt")

if __name__ == "__main__":
    main() 