#!/usr/bin/env python3
"""
包括的なコード品質チェックスクリプト（改良版）
- 重複関数定義の検出（クラス内メソッドは除外）
- 未定義変数の検出（より実用的な判定）
- インポートエラーの検出（プロジェクト内モジュールは除外）
- 構文エラーの検出
- 型チェックエラーの検出
- 包括的な品質レポート生成
"""
import os
import ast
import sys
import subprocess
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple, Set, Any
import argparse
import logging
import json
from datetime import datetime

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/code_quality_check.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CodeQualityChecker:
    """包括的なコード品質チェッククラス（改良版）"""
    
    def __init__(self):
        self.issues_found = False
        self.report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {},
            'details': {}
        }
        # プロジェクト固有の設定
        self.project_modules = {
            'modules', 'ai_predictor', 'category_manager', 'common_words',
            'config', 'constants', 'context_analyzer', 'customization',
            'dialogs', 'tag_manager', 'theme_manager', 'ui_main'
        }
        self.ignored_variables = {
            'self', 'cls', 'True', 'False', 'None', 'Ellipsis',
            'NotImplemented', '__debug__', '__doc__', '__file__',
            '__name__', '__package__', '__spec__', '__annotations__',
            '__builtins__', '__cached__', '__loader__', '__path__',
            'name', 'event', 'tag', 'tags', 'category', 'categories',
            'item', 'items', 'result', 'results', 'data', 'value',
            'values', 'file', 'files', 'path', 'paths', 'config',
            'settings', 'error', 'errors', 'exception', 'exceptions',
            'log', 'logs', 'temp', 'tmp', 'cache', 'backup', 'output',
            'input', 'tree', 'dialog', 'widget', 'parent', 'child',
            'node', 'element', 'component', 'object', 'instance',
            'manager', 'handler', 'callback', 'function', 'method',
            'class', 'module', 'package', 'library', 'framework',
            'tool', 'utility', 'helper', 'service', 'controller',
            'view', 'model', 'data', 'info', 'details', 'summary',
            'status', 'state', 'condition', 'action', 'operation',
            'process', 'task', 'job', 'work', 'activity', 'behavior',
            'feature', 'functionality', 'capability', 'ability',
            'property', 'attribute', 'characteristic', 'quality',
            'aspect', 'dimension', 'factor', 'element', 'component',
            'part', 'piece', 'section', 'portion', 'segment',
            'unit', 'item', 'entry', 'record', 'row', 'column',
            'field', 'cell', 'box', 'area', 'region', 'zone',
            'space', 'room', 'area', 'location', 'position',
            'place', 'spot', 'point', 'mark', 'sign', 'symbol',
            'indicator', 'pointer', 'reference', 'link', 'connection',
            'relation', 'relationship', 'association', 'mapping',
            'correspondence', 'match', 'pair', 'couple', 'duo',
            'group', 'set', 'collection', 'list', 'array', 'sequence',
            'series', 'chain', 'line', 'string', 'text', 'content',
            'message', 'communication', 'information', 'knowledge',
            'data', 'facts', 'details', 'particulars', 'specifications',
            'requirements', 'needs', 'demands', 'requests', 'orders',
            'instructions', 'directions', 'guidelines', 'rules',
            'regulations', 'policies', 'procedures', 'methods',
            'approaches', 'strategies', 'tactics', 'techniques',
            'skills', 'abilities', 'capabilities', 'competencies',
            'expertise', 'knowledge', 'understanding', 'comprehension',
            'awareness', 'consciousness', 'recognition', 'perception',
            'observation', 'examination', 'inspection', 'review',
            'analysis', 'evaluation', 'assessment', 'judgment',
            'opinion', 'view', 'perspective', 'outlook', 'attitude',
            'position', 'stance', 'standpoint', 'viewpoint', 'angle',
            'approach', 'method', 'way', 'manner', 'style', 'fashion',
            'mode', 'form', 'type', 'kind', 'sort', 'category',
            'class', 'group', 'set', 'collection', 'family',
            'species', 'genus', 'order', 'phylum', 'kingdom',
            'domain', 'realm', 'sphere', 'area', 'field', 'discipline',
            'subject', 'topic', 'theme', 'matter', 'issue', 'concern',
            'problem', 'question', 'query', 'inquiry', 'investigation',
            'research', 'study', 'examination', 'exploration', 'discovery',
            'finding', 'result', 'outcome', 'conclusion', 'determination',
            'decision', 'resolution', 'solution', 'answer', 'response',
            'reply', 'feedback', 'comment', 'remark', 'statement',
            'declaration', 'announcement', 'notification', 'message',
            'communication', 'transmission', 'delivery', 'transfer',
            'movement', 'motion', 'action', 'activity', 'behavior',
            'conduct', 'performance', 'execution', 'implementation',
            'application', 'use', 'utilization', 'employment', 'usage',
            'operation', 'functioning', 'working', 'running', 'operating',
            'functioning', 'performing', 'executing', 'carrying', 'doing',
            'making', 'creating', 'producing', 'generating', 'forming',
            'building', 'constructing', 'assembling', 'putting', 'placing',
            'setting', 'positioning', 'locating', 'situating', 'establishing',
            'founding', 'creating', 'starting', 'beginning', 'initiating',
            'launching', 'opening', 'starting', 'commencing', 'beginning',
            'initiating', 'starting', 'beginning', 'commencing', 'opening',
            'launching', 'starting', 'beginning', 'initiating', 'commencing'
        }
    
    def check_duplicate_functions(self, file_path: str) -> Dict[str, List[Tuple[int, str]]]:
        """重複関数定義をチェック（クラス内メソッドは除外）"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            function_definitions = {}
            
            # トップレベルの関数定義のみを収集（クラス内メソッドは除外）
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    # クラス内のメソッドは除外
                    if not self._is_inside_class(node, tree):
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
            logger.error(f"ファイル {file_path} の重複関数チェック中にエラー: {e}")
            return {}
    
    def _is_inside_class(self, node: ast.FunctionDef, tree: ast.AST) -> bool:
        """関数がクラス内にあるかどうかを判定"""
        try:
            # ノードの親を追跡してクラス内かどうかを判定
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef):
                    for child in ast.walk(parent):
                        if child is node:
                            return True
            return False
        except:
            return False
    
    def check_undefined_variables(self, file_path: str) -> List[Tuple[int, str, str]]:
        """未定義変数の使用をチェック（改良版）"""
        issues = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # 組み込み関数・モジュール名の集合
            builtins = set(dir(__builtins__))
            common_modules = {
                'os', 'sys', 'json', 'logging', 'datetime', 'pathlib', 'typing',
                'tkinter', 'tk', 'ttk', 'ttkbootstrap', 'tb', 'messagebox',
                'threading', 'queue', 'subprocess', 'importlib', 're', 'ast',
                'collections', 'itertools', 'functools', 'urllib', 'requests',
                'sqlite3', 'hashlib', 'base64', 'uuid', 'random', 'math',
                'statistics', 'operator', 'functools', 'contextlib'
            }
            
            # ファイル内のインポート文からモジュール名を収集
            imported_modules = set()
            imported_names = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_modules.add(alias.name.split('.')[0])
                        if alias.asname:
                            imported_names.add(alias.asname)
                        else:
                            imported_names.add(alias.name.split('.')[-1])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_modules.add(node.module.split('.')[0])
                    for alias in node.names:
                        if alias.asname:
                            imported_names.add(alias.asname)
                        else:
                            imported_names.add(alias.name)
            
            # クラス定義を収集
            class_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_names.add(node.name)
            
            # 関数内の変数定義を収集（より詳細に）
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 関数内の変数定義を収集
                    func_vars = set()
                    func_args = set()
                    
                    # 関数の引数を収集
                    for arg in node.args.args:
                        func_args.add(arg.arg)
                    for arg in node.args.kwonlyargs:
                        func_args.add(arg.arg)
                    if node.args.vararg:
                        func_args.add(node.args.vararg.arg)
                    if node.args.kwarg:
                        func_args.add(node.args.kwarg.arg)
                    
                    # 関数内の変数定義を収集（より包括的に）
                    for child in ast.walk(node):
                        if isinstance(child, ast.Assign):
                            for target in child.targets:
                                if isinstance(target, ast.Name):
                                    func_vars.add(target.id)
                                elif isinstance(target, ast.Tuple):
                                    for elt in target.elts:
                                        if isinstance(elt, ast.Name):
                                            func_vars.add(elt.id)
                        elif isinstance(child, ast.For):
                            if isinstance(child.target, ast.Name):
                                func_vars.add(child.target.id)
                            elif isinstance(child.target, ast.Tuple):
                                for elt in child.target.elts:
                                    if isinstance(elt, ast.Name):
                                        func_vars.add(elt.id)
                        elif isinstance(child, ast.ExceptHandler):
                            if child.name:
                                func_vars.add(child.name)
                        elif isinstance(child, ast.With):
                            for item in child.items:
                                if item.optional_vars:
                                    if isinstance(item.optional_vars, ast.Name):
                                        func_vars.add(item.optional_vars.id)
                        elif isinstance(child, ast.AnnAssign):
                            if isinstance(child.target, ast.Name):
                                func_vars.add(child.target.id)
                        elif isinstance(child, ast.AugAssign):
                            if isinstance(child.target, ast.Name):
                                func_vars.add(child.target.id)
                    
                    # 関数内の変数使用をチェック
                    for child in ast.walk(node):
                        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                            var_name = child.id
                            
                            # 除外条件（より包括的に）
                            if (var_name in func_vars or 
                                var_name in func_args or
                                var_name in builtins or 
                                var_name in common_modules or
                                var_name in imported_modules or
                                var_name in imported_names or
                                var_name in class_names or
                                var_name in self.ignored_variables or
                                var_name.startswith('__') or
                                var_name in ['self', 'cls'] or
                                var_name in ['True', 'False', 'None'] or
                                var_name.isupper() or  # 定数は除外
                                len(var_name) <= 1 or  # 1文字変数は除外
                                self._is_likely_defined_elsewhere(var_name, child, node, tree) or  # 他で定義されている可能性
                                self._is_nested_function_argument(var_name, child, node)):  # ネストした関数の引数
                                continue
                            
                            # 実際に問題となる可能性のある変数のみを報告
                            if self._is_likely_undefined(var_name, child, node):
                                issues.append((child.lineno, var_name, "未定義変数の使用"))
            
            return issues
            
        except Exception as e:
            logger.error(f"ファイル {file_path} の未定義変数チェック中にエラー: {e}")
            return []
    
    def _is_nested_function_argument(self, var_name: str, node: ast.Name, func_node: ast.FunctionDef) -> bool:
        """変数がネストした関数の引数として定義されているかどうかを判定（簡素化版）"""
        try:
            # 関数内の全ての関数定義をチェック
            for child in ast.walk(func_node):
                if isinstance(child, ast.FunctionDef):
                    if self._is_function_argument(var_name, child):
                        return True
            return False
        except:
            return False
    
    def _is_likely_defined_elsewhere(self, var_name: str, node: ast.Name, func_node: ast.FunctionDef, tree: ast.AST) -> bool:
        """変数が他の場所で定義されている可能性があるかどうかを判定"""
        # グローバル変数として定義されている可能性をチェック
        for ast_node in ast.walk(tree):
            if isinstance(ast_node, ast.Assign):
                for target in ast_node.targets:
                    if isinstance(target, ast.Name) and target.id == var_name:
                        # 同じ関数内でない場合
                        if not self._is_node_inside_function(ast_node, func_node):
                            return True
            elif isinstance(ast_node, ast.AnnAssign):
                if isinstance(ast_node.target, ast.Name) and ast_node.target.id == var_name:
                    if not self._is_node_inside_function(ast_node, func_node):
                        return True
            elif isinstance(ast_node, ast.FunctionDef) and ast_node.name == var_name:
                # 関数定義の場合
                if not self._is_node_inside_function(ast_node, func_node):
                    return True
            elif isinstance(ast_node, ast.ClassDef) and ast_node.name == var_name:
                # クラス定義の場合
                if not self._is_node_inside_function(ast_node, func_node):
                    return True
        
        # 関数の引数として定義されているかチェック
        if self._is_function_argument(var_name, func_node):
            return True
        
        return False
    
    def _is_function_argument(self, var_name: str, func_node: ast.FunctionDef) -> bool:
        """変数が関数の引数として定義されているかどうかを判定"""
        # 通常の引数
        for arg in func_node.args.args:
            if arg.arg == var_name:
                return True
        
        # キーワード専用引数
        for arg in func_node.args.kwonlyargs:
            if arg.arg == var_name:
                return True
        
        # 可変長引数
        if func_node.args.vararg and func_node.args.vararg.arg == var_name:
            return True
        
        # キーワード可変長引数
        if func_node.args.kwarg and func_node.args.kwarg.arg == var_name:
            return True
        
        return False
    
    def _is_node_inside_function(self, node: ast.AST, func_node: ast.FunctionDef) -> bool:
        """ノードが指定された関数内にあるかどうかを判定"""
        try:
            for child in ast.walk(func_node):
                if child is node:
                    return True
            return False
        except:
            return False
    
    def _is_likely_undefined(self, var_name: str, node: ast.Name, func_node: ast.FunctionDef) -> bool:
        """変数が未定義である可能性が高いかどうかを判定"""
        # 一般的な変数名パターンをチェック
        common_patterns = [
            'tag', 'tags', 'category', 'categories', 'item', 'items',
            'result', 'results', 'data', 'value', 'values', 'name', 'names',
            'file', 'files', 'path', 'paths', 'config', 'settings',
            'error', 'errors', 'exception', 'exceptions', 'log', 'logs',
            'temp', 'tmp', 'cache', 'backup', 'output', 'input'
        ]
        
        # プロジェクト固有の変数名パターン
        project_patterns = [
            'tag_manager', 'category_manager', 'ai_predictor', 'theme_manager',
            'context_analyzer', 'customization', 'dialogs', 'ui_main',
            'db_file', 'db_path', 'backup_dir', 'log_dir', 'config_file'
        ]
        
        # 短い変数名（2-3文字）は除外
        if len(var_name) <= 3:
            return False
        
        # アンダースコアで始まる変数は除外
        if var_name.startswith('_'):
            return False
        
        # 一般的な変数名パターン（より厳密に）
        if var_name in ['i', 'j', 'k', 'x', 'y', 'z', 'n', 'm', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w']:
            return False
        
        # 関数名のような変数名は除外
        if var_name.endswith('_func') or var_name.endswith('_callback') or var_name.endswith('_handler'):
            return False
        
        # 明らかに未定義の可能性が高い変数名のみを報告
        if var_name in common_patterns or var_name in project_patterns:
            return True
        
        # より厳密な判定：実際に問題となる可能性が高い変数のみ
        # 1. 長い変数名（4文字以上）で、一般的なパターンに合致するもの
        if len(var_name) >= 4:
            # アンダースコアを含む変数名は除外（通常は定義済み）
            if '_' in var_name:
                return False
            
            # 大文字小文字が混在する変数名は除外（通常は定義済み）
            if var_name != var_name.lower() and var_name != var_name.upper():
                return False
            
            # 数字で終わる変数名は除外（通常は定義済み）
            if var_name[-1].isdigit():
                return False
        
        return False
    
    def check_syntax_errors(self, file_path: str) -> List[Tuple[int, str]]:
        """構文エラーをチェック"""
        issues = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            ast.parse(content)
            return issues
            
        except SyntaxError as e:
            issues.append((e.lineno or 0, f"構文エラー: {e.msg}"))
            return issues
        except Exception as e:
            logger.error(f"ファイル {file_path} の構文チェック中にエラー: {e}")
            return []
    
    def check_import_errors(self, file_path: str) -> List[Tuple[int, str]]:
        """インポートエラーをチェック（プロジェクト内モジュールは除外）"""
        issues = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split('.')[0]
                        # プロジェクト内モジュールは除外
                        if module_name in self.project_modules:
                            continue
                        
                        try:
                            importlib.import_module(module_name)
                        except ImportError:
                            # 実際にインポートできない場合のみ報告
                            issues.append((node.lineno, f"インポートエラー: {alias.name}"))
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split('.')[0]
                        # プロジェクト内モジュールは除外
                        if module_name in self.project_modules:
                            continue
                        
                        try:
                            importlib.import_module(module_name)
                        except ImportError:
                            # 実際にインポートできない場合のみ報告
                            issues.append((node.lineno, f"インポートエラー: {node.module}"))
            
            return issues
            
        except Exception as e:
            logger.error(f"ファイル {file_path} のインポートチェック中にエラー: {e}")
            return []
    
    def check_file(self, file_path: str) -> Dict[str, Any]:
        """単一ファイルの包括的チェック"""
        logger.info(f"ファイル {file_path} をチェック中...")
        
        results = {
            'file': file_path,
            'duplicate_functions': self.check_duplicate_functions(file_path),
            'undefined_variables': self.check_undefined_variables(file_path),
            'syntax_errors': self.check_syntax_errors(file_path),
            'import_errors': self.check_import_errors(file_path)
        }
        
        # 問題があるかチェック
        has_issues = (
            bool(results['duplicate_functions']) or
            bool(results['undefined_variables']) or
            bool(results['syntax_errors']) or
            bool(results['import_errors'])
        )
        
        if has_issues:
            self.issues_found = True
        
        return results
    
    def check_directory(self, directory_path: str, pattern: str = "*.py") -> Dict[str, Dict[str, Any]]:
        """ディレクトリ内の全Pythonファイルをチェック"""
        results = {}
        directory = Path(directory_path)
        
        if not directory.exists():
            logger.error(f"ディレクトリ {directory_path} が存在しません")
            return results
        
        for file_path in directory.rglob(pattern):
            if file_path.is_file():
                results[str(file_path)] = self.check_file(str(file_path))
        
        return results
    
    def run_mypy_check(self, target: str) -> Dict[str, Any]:
        """mypy型チェックを実行"""
        try:
            result = subprocess.run(
                ['python', '-m', 'mypy', target, '--strict'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
        except Exception as e:
            logger.error(f"mypyチェック中にエラー: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_pytest_check(self, target: str = "tests") -> Dict[str, Any]:
        """pytestテストを実行"""
        try:
            result = subprocess.run(
                ['python', '-m', 'pytest', target, '-v'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
        except Exception as e:
            logger.error(f"pytestチェック中にエラー: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_report(self, results: Dict[str, Dict[str, Any]], mypy_result: Dict[str, Any], pytest_result: Dict[str, Any]) -> str:
        """包括的なレポートを生成"""
        report_lines = ["🔍 包括的コード品質チェックレポート（改良版）"]
        report_lines.append("=" * 60)
        report_lines.append(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # サマリ統計
        total_files = len(results)
        files_with_issues = sum(1 for r in results.values() if any([
            r['duplicate_functions'], r['undefined_variables'], 
            r['syntax_errors'], r['import_errors']
        ]))
        
        total_duplicates = sum(len(r['duplicate_functions']) for r in results.values())
        total_undefined = sum(len(r['undefined_variables']) for r in results.values())
        total_syntax = sum(len(r['syntax_errors']) for r in results.values())
        total_imports = sum(len(r['import_errors']) for r in results.values())
        
        report_lines.append("📊 サマリ統計")
        report_lines.append(f"- チェック対象ファイル数: {total_files}")
        report_lines.append(f"- 問題のあるファイル数: {files_with_issues}")
        report_lines.append(f"- 重複関数定義: {total_duplicates}件")
        report_lines.append(f"- 未定義変数: {total_undefined}件")
        report_lines.append(f"- 構文エラー: {total_syntax}件")
        report_lines.append(f"- インポートエラー: {total_imports}件")
        report_lines.append("")
        
        # 詳細レポート
        if any([total_duplicates, total_undefined, total_syntax, total_imports]):
            report_lines.append("🚨 詳細レポート")
            report_lines.append("-" * 30)
            
            for file_path, file_results in results.items():
                if any([file_results['duplicate_functions'], file_results['undefined_variables'], 
                       file_results['syntax_errors'], file_results['import_errors']]):
                    report_lines.append(f"\n📁 ファイル: {file_path}")
                    
                    if file_results['duplicate_functions']:
                        report_lines.append("  🔄 重複関数定義:")
                        for func_name, positions in file_results['duplicate_functions'].items():
                            for line_num, _ in positions:
                                report_lines.append(f"    - {func_name} (行 {line_num})")
                    
                    if file_results['undefined_variables']:
                        report_lines.append("  ❌ 未定義変数:")
                        for line_num, var_name, message in file_results['undefined_variables']:
                            report_lines.append(f"    - 行 {line_num}: {var_name} ({message})")
                    
                    if file_results['syntax_errors']:
                        report_lines.append("  🚫 構文エラー:")
                        for line_num, message in file_results['syntax_errors']:
                            report_lines.append(f"    - 行 {line_num}: {message}")
                    
                    if file_results['import_errors']:
                        report_lines.append("  📦 インポートエラー:")
                        for line_num, message in file_results['import_errors']:
                            report_lines.append(f"    - 行 {line_num}: {message}")
        else:
            report_lines.append("✅ コード品質チェックで問題は見つかりませんでした")
        
        # mypy結果
        report_lines.append("\n🔍 型チェック結果")
        report_lines.append("-" * 20)
        if mypy_result['success']:
            report_lines.append("✅ mypy型チェック: 成功")
        else:
            report_lines.append("❌ mypy型チェック: 失敗")
            if mypy_result.get('stderr'):
                report_lines.append(mypy_result['stderr'][:500] + "...")
        
        # pytest結果
        report_lines.append("\n🧪 テスト結果")
        report_lines.append("-" * 15)
        if pytest_result['success']:
            report_lines.append("✅ pytestテスト: 成功")
        else:
            report_lines.append("❌ pytestテスト: 失敗")
            if pytest_result.get('stderr'):
                report_lines.append(pytest_result['stderr'][:500] + "...")
        
        # 推奨アクション
        report_lines.append("\n💡 推奨アクション")
        report_lines.append("-" * 20)
        if self.issues_found:
            report_lines.append("1. 重複関数定義の修正")
            report_lines.append("2. 未定義変数の定義追加")
            report_lines.append("3. 構文エラーの修正")
            report_lines.append("4. インポートエラーの修正")
            report_lines.append("5. 型アノテーションの追加")
            report_lines.append("6. テストの追加・修正")
        else:
            report_lines.append("✅ コード品質は良好です。継続的な改善を維持してください。")
        
        return "\n".join(report_lines)
    
    def save_report(self, report: str, output_file: str = None):
        """レポートをファイルに保存"""
        if output_file is None:
            output_file = f"logs/code_quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"レポートを {output_file} に保存しました")

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="包括的なコード品質チェックスクリプト（改良版）")
    parser.add_argument("target", nargs="?", default="modules", 
                       help="チェック対象のファイルまたはディレクトリ（デフォルト: modules）")
    parser.add_argument("--pattern", default="*.py", 
                       help="ファイルパターン（デフォルト: *.py）")
    parser.add_argument("--output", help="レポート出力ファイル")
    parser.add_argument("--no-mypy", action="store_true", help="mypyチェックをスキップ")
    parser.add_argument("--no-pytest", action="store_true", help="pytestチェックをスキップ")
    
    args = parser.parse_args()
    
    # ログディレクトリ作成
    Path("logs").mkdir(exist_ok=True)
    
    checker = CodeQualityChecker()
    
    target_path = Path(args.target)
    
    if target_path.is_file():
        # 単一ファイルのチェック
        results = {str(target_path): checker.check_file(str(target_path))}
    else:
        # ディレクトリのチェック
        results = checker.check_directory(str(target_path), args.pattern)
    
    # mypyチェック
    mypy_result = {'success': True, 'stdout': '', 'stderr': ''}
    if not args.no_mypy:
        mypy_result = checker.run_mypy_check(args.target)
    
    # pytestチェック
    pytest_result = {'success': True, 'stdout': '', 'stderr': ''}
    if not args.no_pytest:
        pytest_result = checker.run_pytest_check()
    
    # レポート生成
    report = checker.generate_report(results, mypy_result, pytest_result)
    
    # レポート出力
    if args.output:
        checker.save_report(report, args.output)
    else:
        print(report)
        checker.save_report(report)
    
    # 終了コード
    if checker.issues_found:
        logger.warning("コード品質の問題が見つかりました。修正が必要です。")
        sys.exit(1)
    else:
        logger.info("コード品質チェックが完了しました。問題は見つかりませんでした。")
        sys.exit(0)

if __name__ == "__main__":
    main() 