@echo off
REM ═══════════════════════════════════════════════════════════
REM run.bat — Graph Structure Visualizer — Windows Runner
REM ═══════════════════════════════════════════════════════════
REM
REM Activates the virtual environment and starts either the
REM Django or Flask development server.
REM
REM Usage:
REM   run.bat              (defaults to Django)
REM   run.bat django       (Django on port 8000)
REM   run.bat flask        (Flask  on port 5001)
REM   run.bat test         (run pytest test suite)
REM   run.bat reinstall    (reinstall all components)
REM
REM ═══════════════════════════════════════════════════════════

setlocal enabledelayedexpansion

REM ── Resolve project root ────────────────────────────────
set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "VENV_DIR=%PROJECT_ROOT%\venv"

REM ── Check venv exists ──────────────────────────────────
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at %VENV_DIR%
    echo [ERROR] Run  setup.bat  first to create the environment.
    pause
    exit /b 1
)

REM ── Activate venv ──────────────────────────────────────
call "%VENV_DIR%\Scripts\activate.bat"

REM ── Parse argument (default: django) ───────────────────
set "MODE=%~1"
if "%MODE%"=="" set "MODE=django"

REM ── Convert to lowercase ───────────────────────────────
for %%a in (a b c d e f g h i j k l m n o p q r s t u v w x y z) do (
    set "MODE=!MODE:%%a=%%a!"
)

REM ── Route to the chosen mode ───────────────────────────

if "%MODE%"=="django"    goto :DJANGO
if "%MODE%"=="flask"     goto :FLASK
if "%MODE%"=="test"      goto :TEST
if "%MODE%"=="tests"     goto :TEST
if "%MODE%"=="reinstall" goto :REINSTALL

goto :USAGE


REM ═══════════════════════════════════════════════════════
:DJANGO
REM ═══════════════════════════════════════════════════════
echo.
echo ===================================================
echo   Starting Django Development Server
echo   http://127.0.0.1:8000/
echo ===================================================
echo.

pushd "%PROJECT_ROOT%\graph_django_app"

REM Run migrations silently in case of first run
python manage.py migrate --run-syncdb 2>nul

echo [INFO]  Server starting on http://127.0.0.1:8000/
echo [INFO]  Press Ctrl+C to stop.
echo.

python manage.py runserver 0.0.0.0:8000
popd
goto :END


REM ═══════════════════════════════════════════════════════
:FLASK
REM ═══════════════════════════════════════════════════════
echo.
echo ===================================================
echo   Starting Flask Development Server
echo   http://127.0.0.1:5001/
echo ===================================================
echo.

pushd "%PROJECT_ROOT%\graph_flask_app"

echo [INFO]  Server starting on http://127.0.0.1:5001/
echo [INFO]  Press Ctrl+C to stop.
echo.

python app.py
popd
goto :END


REM ═══════════════════════════════════════════════════════
:TEST
REM ═══════════════════════════════════════════════════════
echo.
echo ===================================================
echo   Running Test Suite
echo ===================================================
echo.

pushd "%PROJECT_ROOT%"
pytest tests\ -v --tb=short
popd
goto :END


REM ═══════════════════════════════════════════════════════
:REINSTALL
REM ═══════════════════════════════════════════════════════
echo.
echo ===================================================
echo   Reinstalling All Components
echo ===================================================
echo.

echo [INFO]  Uninstalling old packages...
pip uninstall -y graph-visualizer-api graph-visualizer-core data-source-plugin-json data-source-plugin-xml data-source-plugin-rdf-turtle simple-visualizer block-visualizer 2>nul

echo [INFO]  Cleaning build artifacts...
for /d /r "%PROJECT_ROOT%" %%d in (*.egg-info) do (
    if exist "%%d" rmdir /s /q "%%d"
)
for /d /r "%PROJECT_ROOT%" %%d in (build) do (
    if exist "%%d" rmdir /s /q "%%d"
)
for /d /r "%PROJECT_ROOT%" %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d"
)

echo [INFO]  Reinstalling all components...
pip install -e "%PROJECT_ROOT%\api"
pip install -e "%PROJECT_ROOT%\core"
pip install -e "%PROJECT_ROOT%\data_source_plugin_json"
pip install -e "%PROJECT_ROOT%\data_source_plugin_xml"
pip install -e "%PROJECT_ROOT%\data_source_plugin_rdf"
pip install -e "%PROJECT_ROOT%\simple_visualizer"
pip install -e "%PROJECT_ROOT%\block_visualizer"

echo.
echo [INFO]  Reinstallation complete!
echo [INFO]  Installed packages:
pip list --format=columns 2>nul | findstr /i "graph-visualizer data-source simple-visualizer block-visualizer"
echo.
goto :END


REM ═══════════════════════════════════════════════════════
:USAGE
REM ═══════════════════════════════════════════════════════
echo.
echo Usage: run.bat [django^|flask^|test^|reinstall]
echo.
echo   django      Start Django development server (port 8000) [default]
echo   flask       Start Flask development server  (port 5001)
echo   test        Run the pytest test suite
echo   reinstall   Uninstall ^& reinstall all project components
echo.
goto :END


:END
endlocal
