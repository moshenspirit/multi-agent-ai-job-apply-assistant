@echo off
title BOSS Collect Agent
cd /d "%~dp0"

echo ==========================================
echo    BOSS Collect Agent
echo ==========================================
echo.
echo Before collect, please check:
echo   1. PC connected to phone HOTSPOT
echo   2. Clash/Proxy CLOSED
echo   3. Special Chrome LOGGED IN
echo.

set KEYWORD=
set CITY=
set PAGES=

set /p KEYWORD=Keyword [Enter=AI-develop]:
set /p CITY=City [Enter=Guangzhou]:
set /p PAGES=Pages [Enter=1, max 3]:

if not defined PAGES set PAGES=1

echo.
echo ------------------------------------------
echo   Collecting: %KEYWORD% / %CITY% / %PAGES% pages
echo ------------------------------------------
echo.

REM 探测 Python：优先 PYTHON_EXE 环境变量，否则用 PATH 中的 python
set "PY=python"
if not "%PYTHON_EXE%"=="" set "PY=%PYTHON_EXE%"
where %PY% >nul 2>nul
if errorlevel 1 (
    echo [ERROR] python not found. Set PYTHON_EXE or add Python to PATH.
    pause
    exit /b 1
)

%PY% scripts\run_collector.py --keyword "%KEYWORD%" --city "%CITY%" --pages %PAGES%

echo.
echo Done! Result printed above.
pause
