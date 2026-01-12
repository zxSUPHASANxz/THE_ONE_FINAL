# THE_ONE Quick Start Script
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
    docker run -d --name ngrok_django `
        -e NGROK_AUTHTOKEN=32Gc9AiZAGtTZ8yyE8zzbVYAi0B_66EmP2knS61uxe38eYN8J `
        -p 4040:4040 `
        ngrok/ngrok:latest http host.docker.internal:8000
    
    Start-Sleep -Seconds 10
    $response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -UseBasicParsing
    $url = $response.tunnels[0].public_url
    
    # Save to .env
    @"
NGROK_URL=$url
NGROK_AUTHTOKEN=32Gc9AiZAGtTZ8yyE8zzbVYAi0B_66EmP2knS61uxe38eYN8J
N8N_WEBHOOK_URL=http://localhost:5678/webhook/chatbot-rag
GEMINI_API_KEY=AIzaSyDu2sGMNZPdAIhZUp0tsZ_7DrKDPqhwhtY
"@ | Set-Content .env
}

Write-Host "`n=== THE_ONE IS READY ===`n" -ForegroundColor Green
Write-Host "Public URL: " -NoNewline -ForegroundColor Yellow
Write-Host "$url" -ForegroundColor Cyan
Write-Host "Local URL:  http://localhost:8000`n" -ForegroundColor White
