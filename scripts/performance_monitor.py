#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
パフォーマンス監視スクリプト
アプリケーションのパフォーマンスを監視・分析する機能
"""

import os
import sys
import time
import psutil
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading
import queue

class PerformanceMonitor:
    """パフォーマンス監視クラス"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.logs_dir = self.project_root / "logs"
        self.data_dir = self.project_root / "data"
        
        # ログディレクトリを作成
        self.logs_dir.mkdir(exist_ok=True)
        
        # パフォーマンスデータ
        self.performance_data = []
        self.monitoring = False
        self.monitor_thread = None
        self.data_queue = queue.Queue()
        
    def get_system_info(self) -> Dict:
        """システム情報を取得"""
        try:
            return {
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_usage": psutil.disk_usage('/').percent,
                "platform": sys.platform,
                "python_version": sys.version
            }
        except Exception as e:
            print(f"⚠️  システム情報取得中にエラー: {e}")
            return {}
            
    def get_process_info(self) -> Dict:
        """現在のプロセス情報を取得"""
        try:
            process = psutil.Process()
            return {
                "cpu_percent": process.cpu_percent(),
                "memory_percent": process.memory_percent(),
                "memory_rss": process.memory_info().rss,
                "threads": process.num_threads(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections())
            }
        except Exception as e:
            print(f"⚠️  プロセス情報取得中にエラー: {e}")
            return {}
            
    def get_database_info(self) -> Dict:
        """データベース情報を取得"""
        db_info = {}
        try:
            db_file = self.data_dir / "tags.db"
            if db_file.exists():
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                # テーブル情報
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                db_info["tables"] = [table[0] for table in tables]
                
                # タグ数
                cursor.execute("SELECT COUNT(*) FROM tags")
                tag_count = cursor.fetchone()[0]
                db_info["tag_count"] = tag_count
                
                # データベースサイズ
                db_info["file_size"] = db_file.stat().st_size
                
                # インデックス情報
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
                indexes = cursor.fetchall()
                db_info["indexes"] = [index[0] for index in indexes]
                
                conn.close()
                
        except Exception as e:
            print(f"⚠️  データベース情報取得中にエラー: {e}")
            
        return db_info
        
    def measure_function_performance(self, func, *args, **kwargs) -> Tuple[any, float]:
        """関数の実行時間を測定"""
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            return result, execution_time
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"⚠️  関数実行中にエラー: {e}")
            return None, execution_time
            
    def collect_performance_data(self) -> Dict:
        """パフォーマンスデータを収集"""
        timestamp = datetime.now().isoformat()
        
        data = {
            "timestamp": timestamp,
            "system": self.get_system_info(),
            "process": self.get_process_info(),
            "database": self.get_database_info()
        }
        
        return data
        
    def monitor_performance(self, interval: int = 5, duration: Optional[int] = None):
        """パフォーマンスを継続監視"""
        self.monitoring = True
        start_time = time.time()
        
        print(f"🚀 パフォーマンス監視を開始 (間隔: {interval}秒)")
        
        while self.monitoring:
            try:
                data = self.collect_performance_data()
                self.performance_data.append(data)
                self.data_queue.put(data)
                
                # 監視時間のチェック
                if duration and (time.time() - start_time) > duration:
                    break
                    
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n⚠️  監視が中断されました")
                break
            except Exception as e:
                print(f"⚠️  監視中にエラー: {e}")
                time.sleep(interval)
                
        self.monitoring = False
        print("✅ パフォーマンス監視を終了しました")
        
    def start_monitoring(self, interval: int = 5, duration: Optional[int] = None):
        """監視を開始（非同期）"""
        if self.monitoring:
            print("⚠️  既に監視中です")
            return
            
        self.monitor_thread = threading.Thread(
            target=self.monitor_performance,
            args=(interval, duration)
        )
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """監視を停止"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
            
    def save_performance_data(self, filename: Optional[str] = None) -> str:
        """パフォーマンスデータを保存"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_data_{timestamp}.json"
            
        file_path = self.logs_dir / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.performance_data, f, indent=2, ensure_ascii=False)
                
            print(f"✅ パフォーマンスデータを保存: {filename}")
            return str(file_path)
            
        except Exception as e:
            print(f"❌ パフォーマンスデータの保存に失敗: {e}")
            return ""
            
    def load_performance_data(self, filename: str) -> bool:
        """パフォーマンスデータを読み込み"""
        file_path = self.logs_dir / filename
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.performance_data = json.load(f)
                
            print(f"✅ パフォーマンスデータを読み込み: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ パフォーマンスデータの読み込みに失敗: {e}")
            return False
            
    def analyze_performance(self) -> Dict:
        """パフォーマンスデータを分析"""
        if not self.performance_data:
            return {}
            
        analysis = {
            "total_samples": len(self.performance_data),
            "monitoring_duration": None,
            "cpu_usage": {},
            "memory_usage": {},
            "database_performance": {}
        }
        
        try:
            # 監視時間を計算
            if len(self.performance_data) >= 2:
                start_time = datetime.fromisoformat(self.performance_data[0]["timestamp"])
                end_time = datetime.fromisoformat(self.performance_data[-1]["timestamp"])
                analysis["monitoring_duration"] = str(end_time - start_time)
                
            # CPU使用率の分析
            cpu_values = [data["process"]["cpu_percent"] for data in self.performance_data 
                         if "process" in data and "cpu_percent" in data["process"]]
            if cpu_values:
                analysis["cpu_usage"] = {
                    "average": sum(cpu_values) / len(cpu_values),
                    "max": max(cpu_values),
                    "min": min(cpu_values)
                }
                
            # メモリ使用率の分析
            memory_values = [data["process"]["memory_percent"] for data in self.performance_data 
                           if "process" in data and "memory_percent" in data["process"]]
            if memory_values:
                analysis["memory_usage"] = {
                    "average": sum(memory_values) / len(memory_values),
                    "max": max(memory_values),
                    "min": min(memory_values)
                }
                
            # データベースパフォーマンスの分析
            tag_counts = [data["database"]["tag_count"] for data in self.performance_data 
                         if "database" in data and "tag_count" in data["database"]]
            if tag_counts:
                analysis["database_performance"] = {
                    "average_tag_count": sum(tag_counts) / len(tag_counts),
                    "max_tag_count": max(tag_counts),
                    "min_tag_count": min(tag_counts)
                }
                
        except Exception as e:
            print(f"⚠️  パフォーマンス分析中にエラー: {e}")
            
        return analysis
        
    def generate_performance_report(self) -> str:
        """パフォーマンスレポートを生成"""
        analysis = self.analyze_performance()
        
        if not analysis:
            return "パフォーマンスデータがありません"
            
        report = []
        report.append("📊 パフォーマンス分析レポート")
        report.append("=" * 50)
        report.append(f"サンプル数: {analysis.get('total_samples', 0)}")
        report.append(f"監視時間: {analysis.get('monitoring_duration', 'N/A')}")
        report.append("")
        
        # CPU使用率
        cpu_usage = analysis.get("cpu_usage", {})
        if cpu_usage:
            report.append("🖥️  CPU使用率:")
            report.append(f"  平均: {cpu_usage.get('average', 0):.2f}%")
            report.append(f"  最大: {cpu_usage.get('max', 0):.2f}%")
            report.append(f"  最小: {cpu_usage.get('min', 0):.2f}%")
            report.append("")
            
        # メモリ使用率
        memory_usage = analysis.get("memory_usage", {})
        if memory_usage:
            report.append("💾 メモリ使用率:")
            report.append(f"  平均: {memory_usage.get('average', 0):.2f}%")
            report.append(f"  最大: {memory_usage.get('max', 0):.2f}%")
            report.append(f"  最小: {memory_usage.get('min', 0):.2f}%")
            report.append("")
            
        # データベースパフォーマンス
        db_performance = analysis.get("database_performance", {})
        if db_performance:
            report.append("🗄️  データベースパフォーマンス:")
            report.append(f"  平均タグ数: {db_performance.get('average_tag_count', 0):.0f}")
            report.append(f"  最大タグ数: {db_performance.get('max_tag_count', 0)}")
            report.append(f"  最小タグ数: {db_performance.get('min_tag_count', 0)}")
            
        return "\n".join(report)
        
    def list_performance_files(self) -> List[str]:
        """パフォーマンスファイル一覧を取得"""
        files = []
        try:
            for file_path in self.logs_dir.glob("performance_data_*.json"):
                files.append(file_path.name)
        except Exception as e:
            print(f"⚠️  ファイル一覧取得中にエラー: {e}")
            
        return sorted(files, reverse=True)

def main():
    """メイン関数"""
    monitor = PerformanceMonitor()
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python performance_monitor.py monitor [interval] [duration]  # 監視開始")
        print("  python performance_monitor.py stop                           # 監視停止")
        print("  python performance_monitor.py save [filename]                # データ保存")
        print("  python performance_monitor.py load <filename>                # データ読み込み")
        print("  python performance_monitor.py analyze                        # 分析実行")
        print("  python performance_monitor.py report                         # レポート生成")
        print("  python performance_monitor.py list                           # ファイル一覧")
        sys.exit(1)
        
    command = sys.argv[1]
    
    try:
        if command == "monitor":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            duration = int(sys.argv[3]) if len(sys.argv) > 3 else None
            monitor.start_monitoring(interval, duration)
            
            # 監視中は待機
            try:
                while monitor.monitoring:
                    time.sleep(1)
            except KeyboardInterrupt:
                monitor.stop_monitoring()
                
        elif command == "stop":
            monitor.stop_monitoring()
            
        elif command == "save":
            filename = sys.argv[2] if len(sys.argv) > 2 else None
            monitor.save_performance_data(filename)
            
        elif command == "load":
            if len(sys.argv) < 3:
                print("❌ 読み込むファイル名を指定してください")
                sys.exit(1)
            filename = sys.argv[2]
            monitor.load_performance_data(filename)
            
        elif command == "analyze":
            analysis = monitor.analyze_performance()
            print(json.dumps(analysis, indent=2, ensure_ascii=False))
            
        elif command == "report":
            report = monitor.generate_performance_report()
            print(report)
            
        elif command == "list":
            files = monitor.list_performance_files()
            print("📋 パフォーマンスファイル一覧:")
            for file in files:
                print(f"  {file}")
                
        else:
            print(f"❌ 不明なコマンド: {command}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  処理が中断されました")
        monitor.stop_monitoring()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 