#!/usr/bin/env python3
"""
継続的監視システム
アプリケーションの動作を継続的に監視し、問題を自動検出
"""

import os
import sys
import time
import json
import logging
import threading
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any
import psutil

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/continuous_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class ContinuousMonitor:
    def __init__(self, check_interval: int = 60):
        self.logger = logging.getLogger(__name__)
        self.check_interval = check_interval  # 秒
        self.monitoring = False
        self.issues = []
        self.start_time = None
        
    def start_monitoring(self):
        """監視開始"""
        self.logger.info("継続的監視システム開始")
        self.monitoring = True
        self.start_time = datetime.now()
        
        try:
            while self.monitoring:
                self.run_health_check()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            self.logger.info("監視を停止します")
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """監視停止"""
        self.monitoring = False
        self.generate_monitoring_report()
    
    def run_health_check(self):
        """ヘルスチェック実行"""
        self.logger.info("ヘルスチェック実行中...")
        
        # 1. ファイル整合性チェック
        self.check_file_integrity()
        
        # 2. データベース整合性チェック
        self.check_database_integrity()
        
        # 3. 設定ファイルチェック
        self.check_config_files()
        
        # 4. ログファイルチェック
        self.check_log_files()
        
        # 5. メモリ使用量チェック
        self.check_memory_usage()
        
        # 6. ディスク容量チェック
        self.check_disk_space()
    
    def check_file_integrity(self):
        """ファイル整合性チェック"""
        critical_files = [
            "main.py",
            "modules/ui_main.py",
            "modules/tag_manager.py",
            "modules/theme_manager.py",
            "modules/customization.py",
            "resources/config/categories.json",
            "resources/config/theme_settings.json"
        ]
        
        for file_path in critical_files:
            if not os.path.exists(file_path):
                self.add_issue("missing_file", f"重要なファイルが見つかりません: {file_path}")
            elif os.path.getsize(file_path) == 0:
                self.add_issue("empty_file", f"ファイルが空です: {file_path}")
    
    def check_database_integrity(self):
        """データベース整合性チェック"""
        db_files = [
            "modules/data/tags.db",
            "resources/tags.db"
        ]
        
        for db_file in db_files:
            if os.path.exists(db_file):
                try:
                    # ファイルサイズチェック
                    size = os.path.getsize(db_file)
                    if size == 0:
                        self.add_issue("empty_database", f"データベースが空です: {db_file}")
                    elif size > 100 * 1024 * 1024:  # 100MB以上
                        self.add_issue("large_database", f"データベースが大きすぎます: {db_file} ({size/1024/1024:.1f}MB)")
                        
                except Exception as e:
                    self.add_issue("database_error", f"データベースチェックエラー: {db_file} - {e}")
    
    def check_config_files(self):
        """設定ファイルチェック"""
        config_files = [
            "resources/config/ai_settings.json",
            "resources/config/theme_settings.json"
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 基本的な構造チェック
                    if not isinstance(data, dict):
                        self.add_issue("invalid_config", f"設定ファイルの形式が不正です: {config_file}")
                        
                except json.JSONDecodeError as e:
                    self.add_issue("json_error", f"JSON形式エラー: {config_file} - {e}")
                except Exception as e:
                    self.add_issue("config_error", f"設定ファイルエラー: {config_file} - {e}")
    
    def check_log_files(self):
        """ログファイルチェック"""
        log_files = [
            "logs/auto_bug_detector.log",
            "logs/continuous_monitor.log"
        ]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    # ログファイルサイズチェック
                    size = os.path.getsize(log_file)
                    if size > 10 * 1024 * 1024:  # 10MB以上
                        self.add_issue("large_log", f"ログファイルが大きすぎます: {log_file} ({size/1024/1024:.1f}MB)")
                    
                    # 最近のエラーログチェック
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        recent_lines = lines[-100:]  # 最後の100行
                        
                        for line in recent_lines:
                            if 'ERROR' in line or 'CRITICAL' in line:
                                self.add_issue("recent_error", f"最近のエラーログ: {line.strip()}")
                                break
                                
                except Exception as e:
                    self.add_issue("log_check_error", f"ログファイルチェックエラー: {log_file} - {e}")
    
    def check_memory_usage(self):
        """メモリ使用量チェック"""
        try:
            memory = psutil.virtual_memory()
            if memory.percent > 80:
                self.add_issue("high_memory", f"メモリ使用量が高いです: {memory.percent}%")
        except Exception as e:
            self.add_issue("memory_check_error", f"メモリチェックエラー: {e}")
    
    def check_disk_space(self):
        """ディスク容量チェック"""
        try:
            disk = psutil.disk_usage('.')
            if disk.percent > 90:
                self.add_issue("low_disk_space", f"ディスク容量が不足しています: {disk.percent}%")
        except Exception as e:
            self.add_issue("disk_check_error", f"ディスクチェックエラー: {e}")
    
    def add_issue(self, issue_type: str, message: str):
        """問題を記録"""
        issue = {
            "type": issue_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "severity": "high" if issue_type in ["missing_file", "database_error"] else "medium"
        }
        
        self.issues.append(issue)
        self.logger.warning(f"問題検出: {issue_type} - {message}")
    
    def generate_monitoring_report(self):
        """監視レポート生成"""
        if not self.start_time:
            return
        
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        report = {
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "total_checks": len(self.issues),
            "issues": self.issues,
            "summary": {
                "high_severity": len([i for i in self.issues if i["severity"] == "high"]),
                "medium_severity": len([i for i in self.issues if i["severity"] == "medium"]),
                "low_severity": len([i for i in self.issues if i["severity"] == "low"])
            }
        }
        
        # レポート保存
        try:
            os.makedirs("logs", exist_ok=True)
            report_file = f"logs/monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"監視レポート保存完了: {report_file}")
            
            # サマリー表示
            print(f"\n=== 監視レポート ===")
            print(f"監視時間: {duration}")
            print(f"総チェック数: {len(self.issues)}")
            print(f"高重要度問題: {report['summary']['high_severity']}")
            print(f"中重要度問題: {report['summary']['medium_severity']}")
            print(f"低重要度問題: {report['summary']['low_severity']}")
            
        except Exception as e:
            self.logger.error(f"レポート保存エラー: {e}")

def main():
    """メイン実行関数"""
    print("継続的監視システム")
    print("Ctrl+C で停止")
    print()
    
    monitor = ContinuousMonitor(check_interval=60)  # 1分間隔
    
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n監視を停止します...")
        monitor.stop_monitoring()

if __name__ == "__main__":
    main() 