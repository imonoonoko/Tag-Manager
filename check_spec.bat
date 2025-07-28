@echo off
echo ========================================
echo 自動不具合防止・仕様整合性チェック開始
echo ========================================

echo.
echo [1/6] 重複関数定義チェック...
python scripts/check_duplicate_functions.py modules
if %errorlevel% neq 0 (
    echo 重複関数定義が見つかりました。修正が必要です。
    pause
    exit /b 1
)
echo 重複関数定義チェック完了

echo.
echo [2/6] 包括的コード品質チェック（改良版）...
python scripts/check_code_quality.py modules --no-mypy --no-pytest
if %errorlevel% neq 0 (
    echo コード品質の問題が見つかりました。修正が必要です。
    pause
    exit /b 1
)
echo 包括的コード品質チェック完了

echo.
echo [3/6] 仕様書整合性チェック...
python scripts/check_spec_compliance.py
if %errorlevel% neq 0 (
    echo 仕様書整合性チェックでエラーが発生しました。
    pause
    exit /b 1
)
echo 仕様書整合性チェック完了

echo.
echo [4/6] 型チェック...
python -m mypy modules/ --strict
if %errorlevel% neq 0 (
    echo 型チェックでエラーが発生しました。
    pause
    exit /b 1
)
echo 型チェック完了

echo.
echo [5/6] テスト実行...
python -m pytest tests/ -v
if %errorlevel% neq 0 (
    echo テストでエラーが発生しました。
    pause
    exit /b 1
)
echo テスト完了

echo.
echo [6/6] 構文チェック...
python -m py_compile modules/ui_main.py
python -m py_compile modules/tag_manager.py
python -m py_compile modules/ai_predictor.py
if %errorlevel% neq 0 (
    echo 構文チェックでエラーが発生しました。
    pause
    exit /b 1
)
echo 構文チェック完了

echo.
echo ========================================
echo 全てのチェックが完了しました！
echo ========================================
pause 