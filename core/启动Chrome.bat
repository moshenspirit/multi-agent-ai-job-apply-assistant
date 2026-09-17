@echo off
title BOSS Setup Chrome
cd /d "%~dp0"

echo ==========================================
echo    Start special Chrome for BOSS collect
echo    (Run this ONCE, keeps login state)
echo ==========================================
echo.
echo Make sure:
echo   1. Phone HOTSPOT connected
echo   2. Clash/Proxy CLOSED
echo   3. First time: will ask you to scan QR login on zhipin.com
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
%PY% ..\tools\boss-zhipin-scraper\scripts\boss_cdp_raw.py --setup-chrome

echo.
echo Setup done! Chrome should be open with BOSS login page.
echo If you just logged in, keep Chrome open, then run "crawl_once.bat" to collect.
pause
