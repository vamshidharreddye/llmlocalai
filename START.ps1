# Local AI Chatbot - PowerShell Launcher
# This script starts all required services

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Local AI Chatbot Launcher" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from python.org" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Ollama
Write-Host "Checking Ollama connection..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✓ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "⚠ WARNING: Ollama doesn't appear to be running" -ForegroundColor Yellow
    Write-Host "  Please start Ollama first: ollama serve" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host ""
Write-Host "Starting Local AI Chatbot services..." -ForegroundColor Cyan
Write-Host ""

# Start Ollama
Write-Host "[1/3] Starting Ollama on http://localhost:11434" -ForegroundColor Green
Start-Process cmd -ArgumentList "/k", "ollama serve" -WindowTitle "Local AI - Ollama"

Start-Sleep -Seconds 3

# Start Backend
Write-Host "[2/3] Starting Backend API on http://127.0.0.1:8000" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; python -m uvicorn app_simple:app --host 127.0.0.1 --port 8000" -WindowTitle "Local AI - Backend"

Start-Sleep -Seconds 2

# Start React Dev Server
Write-Host "[3/3] Starting React Dev Server on http://localhost:5173" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev" -WindowTitle "Local AI - React UI"

Start-Sleep -Seconds 3

# Open browser
Write-Host "Opening browser..." -ForegroundColor Yellow
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "✓ Services started!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "React UI: http://localhost:5173" -ForegroundColor Cyan
Write-Host "UI:       http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Tip: Keep these windows open. Press Ctrl+C to stop any service." -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to exit this launcher"
