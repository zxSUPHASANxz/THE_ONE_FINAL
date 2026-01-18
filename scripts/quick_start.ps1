# THE_ONE Quick Start Script (moved to scripts/)
# Run this script to start Django and ngrok together

Write-Host "`nStarting THE_ONE..." -ForegroundColor Cyan

# Check if Django is already running
$djangoRunning = netstat -ano | Select-String ":8000.*LISTEN"
if (-not $djangoRunning) {
    Write-Host "Starting Django server..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\.venv\Scripts\Activate.ps1; python manage.py runserver 0.0.0.0:8000"
    Start-Sleep -Seconds 8
}

# Check if ngrok is already running
$ngrokRunning = docker ps --filter "name=ngrok_django" --format "{{.Names}}"
if ($ngrokRunning -eq "ngrok_django") {
    Write-Host "ngrok is already running" -ForegroundColor Green
    $response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -UseBasicParsing
    $url = $response.tunnels[0].public_url
} else {
    Write-Host "Starting ngrok..." -ForegroundColor Yellow
    docker rm -f ngrok_django 2>$null
    # Use existing .env for NGROK_AUTHTOKEN and other secrets
    docker run -d --name ngrok_django `
        --env-file .env `
        -p 4040:4040 `
        ngrok/ngrok:latest http host.docker.internal:8000

    Start-Sleep -Seconds 10
    $response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -UseBasicParsing
    $url = $response.tunnels[0].public_url

    # Update only NGROK_URL in .env (preserve other keys)
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
}

Write-Host "`n=== THE_ONE IS READY ===`n" -ForegroundColor Green
Write-Host "Public URL: " -NoNewline -ForegroundColor Yellow
Write-Host "$url" -ForegroundColor Cyan
Write-Host "Local URL:  http://localhost:8000`n" -ForegroundColor White
