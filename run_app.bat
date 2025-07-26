@echo off
setlocal enabledelayedexpansion

rem Move to the script's directory
cd /d "%~dp0"

rem Define virtual environment paths
set "VENV_DIR=%~dp0venv"
set "PYTHON_EXE=!VENV_DIR!\Scripts\python.exe"

rem Check and create virtual environment if it doesn't exist
if not exist "!PYTHON_EXE!" (
    echo Virtual environment not found. Creating one...
    python -m venv "!VENV_DIR!"
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created at !VENV_DIR!.
)

rem Activate virtual environment
call "!VENV_DIR!\Scripts\activate.bat"

rem Upgrade pip
echo Upgrading pip...
"!PYTHON_EXE!" -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    pause
    exit /b 1
)

rem Install required libraries
echo Installing required libraries...
"!PYTHON_EXE!" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo Library installation failed. Check the output above for details.
    pause
    exit /b 1
)

rem Run the application
echo Starting the application...
"!PYTHON_EXE!" -X utf8 "%~dp0main.py"

endlocal
echo Application closed.
pause
