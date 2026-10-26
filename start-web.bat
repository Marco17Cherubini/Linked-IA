@echo off
setlocal enabledelayedexpansion

echo ====================================
echo LinkedIA - Quick Start Web Interface
echo ====================================
echo.

REM Get the directory where the script is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo [1/4] Checking Python environment...
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    pause
    exit /b 1
)

echo [2/4] Installing Flask-CORS...
pip install flask-cors --quiet

echo.
echo [3/4] Starting Backend API Server...

REM Kill any existing process on port 5000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING 2^>nul') do (
    echo Killing existing process on port 5000 (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
)

REM Start backend in a new window with explicit path
start "LinkedIA Backend" cmd /k "cd /d "%SCRIPT_DIR%" && python api_server.py"

echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

REM Verify backend is running
powershell -Command "try { $null = Invoke-WebRequest -Uri 'http://localhost:5000/api/health' -UseBasicParsing -TimeoutSec 5; Write-Host 'Backend OK!' -ForegroundColor Green } catch { Write-Host 'WARNING: Backend may not be ready yet' -ForegroundColor Yellow }"

echo.
echo [4/4] Choose your frontend:
echo   1. React (port 3000)
echo   2. Vue   (port 3001)
echo.
set /p choice="Enter 1 or 2: "

if "%choice%"=="1" (
    echo.
    echo Starting React Frontend...
    cd /d "%SCRIPT_DIR%frontend-react"
    if not exist "node_modules" (
        echo Installing React dependencies...
        call npm install
    )
    start "LinkedIA React" cmd /k "cd /d "%SCRIPT_DIR%frontend-react" && npm run dev"
    echo.
    echo ====================================
    echo Backend: http://localhost:5000
    echo Frontend: http://localhost:3000
    echo ====================================
) else if "%choice%"=="2" (
    echo.
    echo Starting Vue Frontend...
    cd /d "%SCRIPT_DIR%frontend-vue"
    if not exist "node_modules" (
        echo Installing Vue dependencies...
        call npm install
    )
    start "LinkedIA Vue" cmd /k "cd /d "%SCRIPT_DIR%frontend-vue" && npm run dev"
    echo.
    echo ====================================
    echo Backend: http://localhost:5000
    echo Frontend: http://localhost:3001
    echo ====================================
) else (
    echo Invalid choice. Exiting...
    exit /b 1
)

echo.
echo System ready! Check the opened terminals.
echo.
echo TIP: If backend didn't start, run manually:
echo      python api_server.py
echo.
echo Press any key to exit this launcher...
pause >nul
endlocal
