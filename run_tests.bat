@echo off
setlocal

rem Move to the script's directory
cd /d "%~dp0"

rem Set PYTHONPATH to project root for import modules
set PYTHONPATH=%~dp0

rem logsディレクトリがなければ作成
if not exist logs mkdir logs

rem Run pytest for all tests (use global python/pytest)
python -m pytest tests/ --maxfail=3 --disable-warnings -v > logs\pytest.log

if %errorlevel%==0 (
    echo.
    echo All tests passed successfully!
) else (
    echo.
    echo Tests failed. See logs\pytest.log for details.
)

endlocal
pause
