@echo off
REM =============================================================================
REM Mohawk Inference Engine GUI - Windows Build Script
REM Version: 2.1.0 - Production Ready
REM =============================================================================

echo ════════════════════════════════════════════════════════════
echo   MOHAWK INFERENCE ENGINE GUI - Windows Build System v2.1.0
echo ════════════════════════════════════════════════════════════
echo.

REM Check Python version
python --version
echo.

REM Check if virtual environment exists, create if not
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
echo.

REM Build executable with PyInstaller
echo Building standalone executable...
pyinstaller \
    --name=Mohawk-Inference-Engine \
    --onefile \
    --windowed \
    --add-data=mohawk_gui\resources;resources \
    --hidden-import=mohawk_gui.main \
    --hidden-import=mohawk_gui.auth_manager \
    --hidden-import=mohawk_gui.connection_pool \
    --hidden-import=mohawk_gui.metrics_buffer \
    --hidden-import=mohawk_gui.error_recovery \
    --hidden-import=mohawk_gui.monitoring \
    --hidden-import=mohawk_gui.audit_logger \
    mohawk_gui\main.py

echo.
echo ════════════════════════════════════════════════════════════
echo   BUILD COMPLETE!
echo ════════════════════════════════════════════════════════════
echo.
echo Executable location: dist\Mohawk*-Inference-Engine.exe
echo.

REM Show dist directory contents
echo Dist directory contents:
dir /b dist\*.exe 2>nul || echo No executable found

echo.
echo ════════════════════════════════════════════════════════════
echo   NEXT STEPS:
echo ════════════════════════════════════════════════════════════
echo.
echo 1. Copy the executable to your deployment location
echo    Example: copy dist\Mohawk*-Inference-Engine.exe C:\Program Files\Mohawk\
echo.
echo 2. Run the executable (first run will generate auth key)
echo    Mohawk-Inference-Engine.exe --host localhost --port 8003
echo.
echo 3. For production, configure SSL certificates in certs/ directory
echo.
echo 4. Use docker-compose.yml for containerized deployment
echo.
echo ════════════════════════════════════════════════════════════
echo.

pause
