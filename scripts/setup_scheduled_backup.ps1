<#
PowerShell Script to Setup Scheduled Task for Auto Backup (moved to scripts/)
Run this with: .\scripts\setup_scheduled_backup.ps1
#>

Write-Host "="*70 -ForegroundColor Cyan
Write-Host "Setting up Scheduled Backup Task" -ForegroundColor White
Write-Host "="*70 -ForegroundColor Cyan

# Configuration
$scriptPath = "D:\Project\THE__ONE_V3\scheduled_backup.py"
$pythonPath = "D:\Project\THE__ONE_V3\.venv\Scripts\python.exe"
$taskName = "THE_ONE_AutoBackup"
$taskTime = "02:00"  # Run at 2:00 AM daily

Write-Host "`nConfiguration:" -ForegroundColor Yellow
Write-Host "  Script: $scriptPath" -ForegroundColor Gray
Write-Host "  Python: $pythonPath" -ForegroundColor Gray
Write-Host "  Task Name: $taskName" -ForegroundColor Gray
Write-Host "  Schedule: Daily at $taskTime" -ForegroundColor Gray

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "`n⚠️  Task '$taskName' already exists" -ForegroundColor Yellow
    $response = Read-Host "Do you want to replace it? (y/n)"
    
    if ($response -eq 'y') {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "✓ Old task removed" -ForegroundColor Green
    } else {
        Write-Host "✗ Setup cancelled" -ForegroundColor Red
        exit 1
    }
}

# Create scheduled task
try {
    $action = New-ScheduledTaskAction `
        -Execute $pythonPath `
        -Argument $scriptPath `
        -WorkingDirectory "D:\Project\THE__ONE_V3"
    
    $trigger = New-ScheduledTaskTrigger `
        -Daily `
        -At $taskTime
    
    $principal = New-ScheduledTaskPrincipal `
        -UserId $env:USERNAME `
        -LogonType S4U `
        -RunLevel Highest
    
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable
    
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Description "Automatic backup of THE_ONE database embeddings" | Out-Null
    
    Write-Host "`n✓ Scheduled task created successfully!" -ForegroundColor Green
    Write-Host "  The backup will run daily at $taskTime" -ForegroundColor Cyan
    
    # Test run option
    Write-Host "`nDo you want to run a test backup now? (y/n): " -NoNewline -ForegroundColor Yellow
    $testRun = Read-Host
    
    if ($testRun -eq 'y') {
        Write-Host "`nRunning test backup..." -ForegroundColor Cyan
        Start-ScheduledTask -TaskName $taskName
        Start-Sleep -Seconds 2
        
        $taskStatus = Get-ScheduledTask -TaskName $taskName
        Write-Host "✓ Task started. Check logs folder for results." -ForegroundColor Green
    }
    
    Write-Host "`n" + "="*70 -ForegroundColor Cyan
    Write-Host "Setup Complete!" -ForegroundColor Green
    Write-Host "="*70 -ForegroundColor Cyan
    Write-Host "`nUseful commands:" -ForegroundColor Yellow
    Write-Host "  View task: Get-ScheduledTask -TaskName '$taskName'" -ForegroundColor Gray
    Write-Host "  Run now: Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Gray
    Write-Host "  Remove: Unregister-ScheduledTask -TaskName '$taskName'" -ForegroundColor Gray
    Write-Host "  Check logs: Get-ChildItem D:\Project\THE__ONE_V3\logs" -ForegroundColor Gray
    
} catch {
    Write-Host "`n✗ Failed to create scheduled task: $_" -ForegroundColor Red
    exit 1
}
