@echo off
REM ═══════════════════════════════════════════════════════════
REM setup.bat — Graph Structure Visualizer — Windows Setup
REM ═══════════════════════════════════════════════════════════
REM
REM Creates a virtual environment, installs all third-party
REM dependencies, and installs every project component
REM (API, Core/Platform, all Data Source plugins, both
REM Visualizer plugins) in development mode.
REM
REM Usage:
REM   Double-click setup.bat  OR  run from command prompt:
REM   setup.bat
REM
REM After setup completes, use  run.bat  to start the server.
REM ═══════════════════════════════════════════════════════════

setlocal enabledelayedexpansion

REM ── Resolve project root (directory containing this script) ──
set "PROJECT_ROOT=%~dp0"
REM Remove trailing backslash
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "VENV_DIR=%PROJECT_ROOT%\venv"

echo.
echo ===================================================
echo   Graph Structure Visualizer - Windows Setup
echo ===================================================
echo.
echo [INFO]  Project root: %PROJECT_ROOT%

REM ── 1. Check Python is installed ────────────────────────────
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo [ERROR] Download Python 3.8+ from https://www.python.org/downloads/
    echo [ERROR] Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set "PY_VERSION=%%v"
echo [INFO]  Using %PY_VERSION%

REM ── 2. Create virtual environment ──────────────────────────
if exist "%VENV_DIR%" (
    echo [WARN]  Virtual environment already exists at %VENV_DIR%
    set /p RECREATE="  Recreate it? [y/N]: "
    if /i "!RECREATE!"=="y" (
        echo [INFO]  Removing old virtual environment...
        rmdir /s /q "%VENV_DIR%"
        echo [INFO]  Creating new virtual environment...
        python -m venv "%VENV_DIR%"
    )
) else (
    echo [INFO]  Creating virtual environment at %VENV_DIR% ...
    python -m venv "%VENV_DIR%"
)

REM ── 3. Activate virtual environment ────────────────────────
echo [INFO]  Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

REM ── 4. Upgrade pip ^& setuptools ────────────────────────────
echo [INFO]  Upgrading pip and setuptools...
pip install --upgrade pip setuptools wheel

REM ── 5. Install third-party dependencies ────────────────────
echo [INFO]  Installing third-party dependencies from requirements.txt ...
pip install -r "%PROJECT_ROOT%\requirements.txt"

REM ── 6. Install project components (development mode) ───────
REM Order matters: API first, then Core, then plugins.

echo [INFO]  Installing API library...
pip install -e "%PROJECT_ROOT%\api"

echo [INFO]  Installing Core platform...
pip install -e "%PROJECT_ROOT%\core"

echo [INFO]  Installing JSON Data Source plugin...
pip install -e "%PROJECT_ROOT%\data_source_plugin_json"

echo [INFO]  Installing XML Data Source plugin...
pip install -e "%PROJECT_ROOT%\data_source_plugin_xml"

echo [INFO]  Installing RDF Turtle Data Source plugin...
pip install -e "%PROJECT_ROOT%\data_source_plugin_rdf"

echo [INFO]  Installing Simple Visualizer plugin...
pip install -e "%PROJECT_ROOT%\simple_visualizer"

echo [INFO]  Installing Block Visualizer plugin...
pip install -e "%PROJECT_ROOT%\block_visualizer"

REM ── 7. Run Django migrations ───────────────────────────────
echo [INFO]  Running Django migrations...
pushd "%PROJECT_ROOT%\graph_django_app"
python manage.py migrate --run-syncdb 2>nul
popd

REM ── 8. Verify installation ────────────────────────────────
echo.
echo ===================================================
echo   Setup complete!
echo ===================================================
echo.
echo [INFO]  Installed packages:
pip list --format=columns 2>nul | findstr /i "graph-visualizer data-source simple-visualizer block-visualizer"
echo.
echo [INFO]  To start the application, run:
echo           run.bat django     (Django server on port 8000)
echo           run.bat flask      (Flask server on port 5001)
echo.
echo [INFO]  To run tests:
echo           venv\Scripts\activate
echo           pytest tests\ -v
echo.

pause
endlocal
