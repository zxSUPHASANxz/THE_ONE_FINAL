# Wrapper: call consolidated script in ./scripts
$target = Join-Path $PSScriptRoot 'scripts\start_the_one.ps1'
if (Test-Path $target) {
    & $target @args
} else {
    Write-Error "Missing script: $target. Please run scripts/start_the_one.ps1 instead."
    exit 1
}
