@echo off
REM Local AI Chatbot - One-Click Startup Script for Windows
REM This script starts all required services in separate terminals
REM -----------------------------------------------------------------
REM 1) TEMPORARILY ADD OLLAMA + NODE TO PATH FOR THIS SCRIPT ONLY
REM -----------------------------------------------------------------
setlocal

REM 👉 Update these paths if your install locations are different
set "OLLAMA_PATH=C:\Users\VAMSHI\AppData\Local\Programs\Ollama"
set "NODE_PATH=C:\Program Files\nodejs"

REM Extend PATH for all child cmd windows started from this script
set "PATH=%PATH%;%OLLAMA_PATH%;%NODE_PATH%"

echo.
echo ===================================
echo LOCAL AI CHATBOT - STARTUP
echo ===================================
echo.

REM Check if Ollama is available
where ollama >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo WARNING: Ollama not found in PATH
    echo Please add Ollama to your PATH or run:
    echo   powershell .\scripts\add_ollama_to_path.ps1 -Apply
    echo.
    pause
    exit /b 1
)

echo [1/3] Starting Ollama server...
start "Ollama Server" cmd /k "ollama serve"

timeout /t 3 >nul

echo [2/3] Starting Backend API (FastAPI)...
start "Backend API" cmd /k "cd backend && python -m uvicorn app_simple:app --host 127.0.0.1 --port 8000"

timeout /t 2 >nul

echo [3/3] Starting React Dev Server (Vite)...
start "React UI" cmd /k "cd frontend && npm run dev"

timeout /t 3 >nul

echo.
echo ===================================
echo SERVICES STARTED
echo ===================================
echo.
echo Backend:  http://127.0.0.1:8000
echo React UI: http://localhost:5173
echo Ollama:   http://localhost:11434
echo.
echo Opening UI in browser...
timeout /t 2 >nul
start http://localhost:3000

echo.
echo All services are running. Close any terminal to stop that service.
echo To view logs, check the corresponding terminal window.
echo.
pause
