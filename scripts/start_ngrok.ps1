# ====================================
# THE_ONE - Start ngrok for Django (moved to scripts/)
# ====================================

Write-Host "`n╔════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Starting ngrok for THE_ONE...   ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════╝`n" -ForegroundColor Cyan

# Stop old container
Write-Host "[1/3] Cleaning up old ngrok..." -ForegroundColor Yellow
docker rm -f ngrok_django 2>$null

# Start ngrok with localhost (works better than IP)
Write-Host "[2/3] Starting ngrok..." -ForegroundColor Yellow
$containerId = docker run -d --name ngrok_django \
    --env-file .env \
    -p 4040:4040 \
    --network host \
    ngrok/ngrok:latest http 8000

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ ngrok container started" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to start ngrok" -ForegroundColor Red
    exit 1
}

# Wait and get URL
Write-Host "[3/3] Getting public URL..." -ForegroundColor Yellow
Start-Sleep -Seconds 8

try {
    $response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -UseBasicParsing
    $url = $response.tunnels[0].public_url
    
    # Update only NGROK_URL in .env (preserve other keys like NGROK_AUTHTOKEN)
    if (Test-Path .env) {
        $envContent = Get-Content .env -Encoding UTF8
        $hasUrl = $false
        $newContent = $envContent | ForEach-Object {
            if ($_ -match '^NGROK_URL=') {
                $hasUrl = $true
                "NGROK_URL=$url"
            } else {
                $_
            }
        }
        if (-not $hasUrl) { $newContent += "NGROK_URL=$url" }
        $newContent | Set-Content .env -Encoding UTF8
    } else {
        "NGROK_URL=$url" | Set-Content .env -Encoding UTF8
    }
    
    Write-Host "`n╔════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║  ✅ THE_ONE NGROK IS READY!                  ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════╝`n" -ForegroundColor Green
    Write-Host " 🌐 Public URL:" -ForegroundColor Yellow
    Write-Host "    $url`n" -ForegroundColor Cyan
    Write-Host " 📋 URL saved to .env file" -ForegroundColor White
    Write-Host " 💡 Share this URL with users!`n" -ForegroundColor White
    
    return $url
} catch {
    Write-Host "`n❌ Failed to get ngrok URL" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}
