@echo off
echo Tag Manager .exe ビルドツール
echo ============================

REM Pythonが利用可能かチェック
python --version >nul 2>&1
if errorlevel 1 (
    echo エラー: Pythonが見つかりません
    echo Python 3.8以上をインストールしてください
    pause
    exit /b 1
)

echo Pythonが見つかりました
echo.

REM 必要なパッケージをインストール
echo 必要なパッケージをインストール中...
pip install -r requirements.txt
if errorlevel 1 (
    echo エラー: パッケージのインストールに失敗しました
    pause
    exit /b 1
)

echo.
echo ビルドスクリプトを実行中...
python build_exe.py

if errorlevel 1 (
    echo.
    echo エラー: ビルドに失敗しました
    pause
    exit /b 1
)

echo.
echo ビルドが完了しました！
echo dist/Tag-Manager.exe を確認してください
pause 