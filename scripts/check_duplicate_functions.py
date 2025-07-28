#!/usr/bin/env python3
"""
重複関数定義を検出する自動チェックスクリプト
- 指定されたPythonファイル内で同名関数が複数定義されていないかチェック
- 重複定義を発見した場合は詳細レポートを出力
- 今後の開発で重複関数定義によるバグを防止
"""
import os
import ast
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Set
import argparse
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/duplicate_functions.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DuplicateFunctionChecker:
    """重複関数定義を検出するクラス"""
    
    def __init__(self):
        self.duplicates_found = False
    
    def check_file(self, file_path: str) -> Dict[str, List[Tuple[int, str]]]:
        """
        指定されたPythonファイル内の重複関数定義をチェック
        
        Args:
            file_path: チェック対象のPythonファイルパス
            
        Returns:
            重複関数名とその行番号の辞書
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            function_definitions = {}
            
            # トップレベルの関数定義のみを収集
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    line_number = node.lineno
                    
                    if func_name not in function_definitions:
                        function_definitions[func_name] = []
                    
                    function_definitions[func_name].append((line_number, node.name))
            
            # 重複定義をフィルタリング
            duplicates = {
                name: positions for name, positions in function_definitions.items()
                if len(positions) > 1
            }
            
            return duplicates
            
        except Exception as e:
            logger.error(f"ファイル {file_path} の解析中にエラー: {e}")
            return {}
    
    def check_directory(self, directory_path: str, pattern: str = "*.py") -> Dict[str, Dict[str, List[Tuple[int, str]]]]:
        """
        指定されたディレクトリ内の全Pythonファイルをチェック
        
        Args:
            directory_path: チェック対象ディレクトリ
            pattern: ファイルパターン（デフォルト: "*.py"）
            
        Returns:
            ファイルパスと重複関数の辞書
        """
        results = {}
        directory = Path(directory_path)
        
        if not directory.exists():
            logger.error(f"ディレクトリ {directory_path} が存在しません")
            return results
        
        for file_path in directory.rglob(pattern):
            if file_path.is_file():
                duplicates = self.check_file(str(file_path))
                if duplicates:
                    results[str(file_path)] = duplicates
                    self.duplicates_found = True
        
        return results
    
    def generate_report(self, results: Dict[str, Dict[str, List[Tuple[int, str]]]]) -> str:
        """
        重複関数定義のレポートを生成
        
        Args:
            results: チェック結果
            
        Returns:
            レポート文字列
        """
        if not results:
            return "✅ 重複関数定義は見つかりませんでした。"
        
        report_lines = ["🚨 重複関数定義が見つかりました！"]
        report_lines.append("=" * 50)
        
        for file_path, duplicates in results.items():
            report_lines.append(f"\n📁 ファイル: {file_path}")
            report_lines.append("-" * 30)
            
            for func_name, positions in duplicates.items():
                report_lines.append(f"関数名: {func_name}")
                for line_num, _ in positions:
                    report_lines.append(f"  - 行 {line_num}")
                report_lines.append("")
        
        report_lines.append("=" * 50)
        report_lines.append("💡 修正方法:")
        report_lines.append("1. 重複した関数定義のうち、正しい方を残す")
        report_lines.append("2. 不要な関数定義を削除する")
        report_lines.append("3. 関数名が重複している場合は、適切な名前に変更する")
        report_lines.append("4. 修正後、再度このスクリプトを実行して確認する")
        
        return "\n".join(report_lines)

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="重複関数定義を検出するスクリプト")
    parser.add_argument("target", nargs="?", default="modules", 
                       help="チェック対象のファイルまたはディレクトリ（デフォルト: modules）")
    parser.add_argument("--pattern", default="*.py", 
                       help="ファイルパターン（デフォルト: *.py）")
    parser.add_argument("--output", help="レポート出力ファイル")
    
    args = parser.parse_args()
    
    # ログディレクトリ作成
    Path("logs").mkdir(exist_ok=True)
    
    checker = DuplicateFunctionChecker()
    
    target_path = Path(args.target)
    
    if target_path.is_file():
        # 単一ファイルのチェック
        results = {str(target_path): checker.check_file(str(target_path))}
    else:
        # ディレクトリのチェック
        results = checker.check_directory(str(target_path), args.pattern)
    
    # レポート生成
    report = checker.generate_report(results)
    
    # レポート出力
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"レポートを {args.output} に保存しました")
    else:
        print(report)
    
    # 終了コード
    if checker.duplicates_found:
        logger.warning("重複関数定義が見つかりました。修正が必要です。")
        sys.exit(1)
    else:
        logger.info("重複関数定義は見つかりませんでした。")
        sys.exit(0)

if __name__ == "__main__":
    main() 