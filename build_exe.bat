@echo off

echo [INFO] Activating virtual environment...
call .\.venv\Scripts\activate

echo [INFO] Installing PyInstaller...
pip install pyinstaller

echo [INFO] Building the executable...
pyinstaller --noconfirm --onefile --windowed --icon ".\src\icon.ico" ".\src\main.py"

echo [INFO] Deactivating virtual environment...
deactivate

echo [SUCCESS] Build process completed.
pause