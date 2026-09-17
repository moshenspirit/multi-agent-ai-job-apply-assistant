@echo off
title BOSS Matcher
cd /d "%~dp0"

echo ==========================================
echo    Match direction for un-processed jobs
echo    Read config search_keywords, mark each
echo    job as frontend/ai/both/none
echo ==========================================
echo.
echo Will update jobs.match_direction in DB.
echo Press any key to continue, or Ctrl+C to cancel.
pause >nul

REM 探测 Python：优先 PYTHON_EXE 环境变量，否则用 PATH 中的 python
set "PY=python"
if not "%PYTHON_EXE%"=="" set "PY=%PYTHON_EXE%"
where %PY% >nul 2>nul
if errorlevel 1 (
    echo [ERROR] python not found. Set PYTHON_EXE or add Python to PATH.
    pause
    exit /b 1
)

%PY% scripts\run_matcher.py --persist

echo.
echo Matching done! Distribution printed above.
pause
