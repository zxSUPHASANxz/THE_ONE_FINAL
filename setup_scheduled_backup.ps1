# Wrapper: call consolidated script in ./scripts
$target = Join-Path $PSScriptRoot 'scripts\setup_scheduled_backup.ps1'
if (Test-Path $target) {
    & $target @args
} else {
    Write-Error "Missing script: $target. Please run scripts/setup_scheduled_backup.ps1 instead."
    exit 1
}
