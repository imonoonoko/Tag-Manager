@echo off
chcp 65001 >nul
echo 🚀 技術仕様書との整合性チェックを開始...
echo.

REM Pythonスクリプトの実行
if exist "scripts\check_spec_compliance.py" (
    echo 📋 Pythonスクリプトでチェック実行中...
    python scripts\check_spec_compliance.py
    if errorlevel 1 (
        echo.
        echo ❌ チェックで問題が見つかりました
        echo 技術仕様書とAI_REFERENCE_GUIDE.mdを確認してください
        pause
        exit /b 1
    )
) else (
    echo ⚠️  check_spec_compliance.py が見つかりません
)

REM 必須ファイルの存在確認
echo.
echo 📋 必須ファイルの存在確認...
if not exist "技術仕様書_関数・ファイルパス一覧.md" (
    echo ❌ 技術仕様書_関数・ファイルパス一覧.md が見つかりません
    set /a error_count+=1
) else (
    echo ✅ 技術仕様書_関数・ファイルパス一覧.md
)

if not exist "AI_REFERENCE_GUIDE.md" (
    echo ❌ AI_REFERENCE_GUIDE.md が見つかりません
    set /a error_count+=1
) else (
    echo ✅ AI_REFERENCE_GUIDE.md
)

if not exist "ToDoリスト.md" (
    echo ❌ ToDoリスト.md が見つかりません
    set /a error_count+=1
) else (
    echo ✅ ToDoリスト.md
)

REM 重要なモジュールファイルの確認
echo.
echo 📁 重要なモジュールファイルの確認...
if not exist "modules\ui_main.py" (
    echo ❌ modules\ui_main.py が見つかりません
    set /a error_count+=1
) else (
    echo ✅ modules\ui_main.py
)

if not exist "modules\tag_manager.py" (
    echo ❌ modules\tag_manager.py が見つかりません
    set /a error_count+=1
) else (
    echo ✅ modules\tag_manager.py
)

if not exist "modules\dialogs.py" (
    echo ❌ modules\dialogs.py が見つかりません
    set /a error_count+=1
) else (
    echo ✅ modules\dialogs.py
)

if not exist "modules\theme_manager.py" (
    echo ❌ modules\theme_manager.py が見つかりません
    set /a error_count+=1
) else (
    echo ✅ modules\theme_manager.py
)

if not exist "modules\constants.py" (
    echo ❌ modules\constants.py が見つかりません
    set /a error_count+=1
) else (
    echo ✅ modules\constants.py
)

echo.
echo ========================================

if defined error_count (
    echo ❌ %error_count% 個の問題が見つかりました
    echo 技術仕様書とAI_REFERENCE_GUIDE.mdを確認してください
    pause
    exit /b 1
) else (
    echo 🎉 すべてのチェックが完了しました！
    echo 技術仕様書との整合性が確認されました
)

pause 