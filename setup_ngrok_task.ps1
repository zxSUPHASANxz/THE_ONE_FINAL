# ============================================
# สร้าง Scheduled Task สำหรับ reset ngrok ทุก 24 ชม.
# รันไฟล์นี้ด้วย Administrator
# ============================================

$TaskName = "ResetNgrokDaily"
$ScriptPath = "D:\Project\THE__ONE_V3\reset_ngrok.ps1"

# ลบ task เก่าถ้ามี
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# สร้าง action
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$ScriptPath`""

# สร้าง trigger - ทุกวันเวลา 03:00 น.
$trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM

# สร้าง settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# ลงทะเบียน task
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
