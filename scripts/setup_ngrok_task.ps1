# ============================================
# Create Scheduled Task for resetting ngrok daily (moved to scripts/)
# Requires Administrator
# ============================================

$TaskName = "ResetNgrokDaily"
$ScriptPath = "D:\Project\THE__ONE_V3\reset_ngrok.ps1"

# Remove existing task if present
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create action
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$ScriptPath`""

# Create trigger - daily at 00:00
$trigger = New-ScheduledTaskTrigger -Daily -At 12:59:59 AM

# Settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Register task
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Reset ngrok URL and update .env every 24 hours"

Write-Host "`n=================================" -ForegroundColor Green
Write-Host "✓ Scheduled Task created!" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host "Task Name: $TaskName" -ForegroundColor Cyan
Write-Host "Schedule: Daily at 3:00 AM" -ForegroundColor Cyan
Write-Host "Script: $ScriptPath" -ForegroundColor Cyan
Write-Host "`nTo test now, run:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
Write-Host "`nTo remove, run:" -ForegroundColor Yellow
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false" -ForegroundColor White
Write-Host "=================================" -ForegroundColor Green
