@echo off
REM Mohawk Inference Engine GUI - Windows Build Script
REM Version: 2.1.0

echo ════════════════════════════════════════════════════════════
echo   MOHAWK INFERENCE ENGINE GUI - Windows Build System v2.1.0
echo ════════════════════════════════════════════════════════════
echo.

REM Check Python version
python --version
echo.

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
echo.

REM Build executable
echo Building executable...
pyinstaller     --name=Mohawk-Inference-Engine     --onefile     --windowed     --add-data=mohawk_gui\resources;resources     --hidden-import=mohawk_gui.main     --hidden-import=mohawk_gui.auth_manager     --hidden-import=mohawk_gui.connection_pool     --hidden-import=mohawk_gui.metrics_buffer     --hidden-import=mohawk_gui.error_recovery     --hidden-import=mohawk_gui.monitoring     --hidden-import=mohawk_gui.audit_logger     -p mohawk_gui

echo.
echo ════════════════════════════════════════════════════════════
echo   BUILD COMPLETE!
echo ════════════════════════════════════════════════════════════
echo.
echo Executable location: dist\Mohawk*-Inference-Engine.exe
echo.
pause
