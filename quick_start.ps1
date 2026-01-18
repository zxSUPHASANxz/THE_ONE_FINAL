# Wrapper: call consolidated script in ./scripts
$target = Join-Path $PSScriptRoot 'scripts\quick_start.ps1'
if (Test-Path $target) {
    & $target @args
} else {
    Write-Error "Missing script: $target. Please run scripts/quick_start.ps1 instead."
    exit 1
}
