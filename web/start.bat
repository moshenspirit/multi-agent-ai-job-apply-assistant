@echo off
echo ==========================================
echo    BOSS Job Matcher
echo ==========================================
echo.

cd /d "%~dp0"

REM 探测 Python：优先 PYTHON_EXE 环境变量，否则用 PATH 中的 python
set "PY=python"
if not "%PYTHON_EXE%"=="" set "PY=%PYTHON_EXE%"
where %PY% >nul 2>nul
if errorlevel 1 (
    echo [ERROR] python not found. Set PYTHON_EXE or add Python to PATH.
    pause
    exit /b 1
)

echo [1/2] Starting Flask backend...
start "Flask Backend" cmd /c "cd backend && %PY% -m app.app"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Vue frontend...
start "Vue Frontend" cmd /c "cd frontend && npm run dev"

echo.
echo Started!
echo Backend:  http://127.0.0.1:5000
echo Frontend: http://localhost:5173
echo.
pause
