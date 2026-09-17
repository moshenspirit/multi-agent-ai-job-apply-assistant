@echo off
title BOSS Skirmish
cd /d "%~dp0"

echo ==========================================
echo    Generate company risk profiles for
echo    matched jobs (passive + optional LLM)
echo ==========================================
echo.
echo Will update jobs.company_profile in DB.
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

%PY% scripts\run_skirmish.py --persist

echo.
echo Skirmish done! Risk profiles saved to DB.
echo Tip: front-end can show [Copy Profile] button next to each job.
pause
