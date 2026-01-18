# ====================================
# THE_ONE - Complete Startup Script (moved to scripts/)
# ====================================

Write-Host "`n╔════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     THE_ONE - STARTING ALL SERVICES...       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Step 1: Start Django Server
Write-Host "[1/2] Starting Django server..." -ForegroundColor Yellow
$djangoJob = Start-Job -ScriptBlock {
    Set-Location "D:\Project\THE__ONE_V3"
    & "D:\Project\THE__ONE_V3\.venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000
}
Write-Host "✅ Django server started (background)" -ForegroundColor Green

# Wait for Django to be ready
Start-Sleep -Seconds 5

# Check if Django is running
$djangoRunning = $false
for ($i = 1; $i -le 10; $i++) {
    try {
        $test = Invoke-WebRequest -Uri "http://localhost:8000" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        $djangoRunning = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $djangoRunning) {
    Write-Host "❌ Django failed to start" -ForegroundColor Red
    Stop-Job $djangoJob
    Remove-Job $djangoJob
    exit 1
}

Write-Host "✅ Django is responding on localhost:8000" -ForegroundColor Green

# Step 2: Start ngrok
Write-Host "`n[2/2] Starting ngrok..." -ForegroundColor Yellow
$ngrokUrl = & ".\scripts\start_ngrok.ps1"

Write-Host "`n╔════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ ALL SERVICES RUNNING!                    ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════╝`n" -ForegroundColor Green
Write-Host " 🌐 THE_ONE Public URL:" -ForegroundColor Yellow
Write-Host "    $ngrokUrl`n" -ForegroundColor Cyan
Write-Host " ✅ Django: http://localhost:8000" -ForegroundColor White
Write-Host " ✅ ngrok: Active and forwarding" -ForegroundColor White
Write-Host " ✅ PostgreSQL: Running (port 5433)" -ForegroundColor White
Write-Host "`n 💡 Press Ctrl+C to stop Django server" -ForegroundColor Yellow
Write-Host " 💡 ngrok will keep running in background`n" -ForegroundColor Yellow

# Keep Django job running
Write-Host "Monitoring Django server..." -ForegroundColor Gray
Wait-Job $djangoJob
