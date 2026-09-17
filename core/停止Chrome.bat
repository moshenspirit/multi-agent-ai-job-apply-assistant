@echo off
title BOSS Stop Chrome
cd /d "%~dp0"

echo ==========================================
echo    Stop the special BOSS Chrome
echo    (Login state stays on disk, can resume next time)
echo ==========================================
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

REM 依赖第三方 scraper（放置于仓库根 tools/boss-zhipin-scraper，见 README）
%PY% ..\tools\boss-zhipin-scraper\scripts\boss_cdp_raw.py --stop-chrome

echo.
echo Chrome closed. Login state preserved in chrome-profile.
pause
