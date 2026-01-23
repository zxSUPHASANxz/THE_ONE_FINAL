# ====================================
# THE_ONE - Start ngrok for Django
# ====================================

Write-Host "`n╔════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Starting ngrok for THE_ONE...   ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════╝`n" -ForegroundColor Cyan

# Stop old container
Write-Host "[1/3] Cleaning up old ngrok..." -ForegroundColor Yellow
docker rm -f ngrok_django 2>$null

# Start ngrok with localhost (works better than IP)
Write-Host "[2/3] Starting ngrok..." -ForegroundColor Yellow
$containerId = docker run -d --name ngrok_django `
    -e NGROK_AUTHTOKEN=32Gc9AiZAGtTZ8yyE8zzbVYAi0B_66EmP2knS61uxe38eYN8J `
    -p 4040:4040 `
    --network host `
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
    
    # Update .env
    @"
NGROK_URL=$url
NGROK_AUTHTOKEN=32Gc9AiZAGtTZ8yyE8zzbVYAi0B_66EmP2knS61uxe38eYN8J
N8N_WEBHOOK_URL=http://localhost:5678/webhook/chatbot-rag
GEMINI_API_KEY=AIzaSyDu2sGMNZPdAIhZUp0tsZ_7DrKDPqhwhtY
"@ | Set-Content .env
    
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
