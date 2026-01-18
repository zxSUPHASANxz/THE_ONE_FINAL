# ============================================
# Reset ngrok URL and auto-update .env (moved to scripts/)
# ============================================

$PROJECT_PATH = "D:\Project\THE__ONE_V3"
$ENV_FILE = "$PROJECT_PATH\.env"

Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Resetting ngrok URL..." -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Go to project directory
Set-Location $PROJECT_PATH

# 1. Stop and remove ngrok container
Write-Host "`n[1/5] Stopping ngrok container..." -ForegroundColor Yellow
docker stop ngrok_n8n 2>$null
docker rm ngrok_n8n 2>$null

# 2. Start new ngrok
Write-Host "[2/5] Starting new ngrok container..." -ForegroundColor Yellow
docker compose up -d ngrok

# 3. Wait for ngrok to be ready
Write-Host "[3/5] Waiting for ngrok to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 4. Get new URL
Write-Host "[4/5] Getting new ngrok URL..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:4040/api/tunnels" -UseBasicParsing
    $tunnels = ($response.Content | ConvertFrom-Json).tunnels
    $newUrl = $tunnels[0].public_url
    
    Write-Host "Success! New URL: $newUrl" -ForegroundColor Green
    
    # 5. Update .env file
    Write-Host "[5/5] Updating .env file..." -ForegroundColor Yellow
    
    $envContent = Get-Content $ENV_FILE -Encoding UTF8
    $updatedContent = $envContent -replace 'NGROK_URL=https://[a-z0-9]+\.ngrok-free\.app', "NGROK_URL=$newUrl"
    $updatedContent | Set-Content $ENV_FILE -Encoding UTF8
    
    Write-Host "Success! Updated .env file" -ForegroundColor Green
    
    # 6. Restart n8n
    Write-Host "`nRestarting n8n..." -ForegroundColor Yellow
    docker compose restart n8n
    
    Write-Host "`n=================================" -ForegroundColor Green
    Write-Host "SUCCESS! ngrok reset complete!" -ForegroundColor Green
    Write-Host "New URL: $newUrl" -ForegroundColor Green
    Write-Host "=================================" -ForegroundColor Green
    
    # Log
    $logEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - ngrok URL reset: $newUrl"
    Add-Content -Path "$PROJECT_PATH\ngrok_reset.log" -Value $logEntry -Encoding UTF8
    
} catch {
    Write-Host "`nERROR: $_" -ForegroundColor Red
    $errorEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - ERROR: $_"
    Add-Content -Path "$PROJECT_PATH\ngrok_reset.log" -Value $errorEntry -Encoding UTF8
    exit 1
}
