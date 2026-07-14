$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    & (Join-Path $PSScriptRoot "install_console.ps1")
}

Set-Location $RepoRoot
Write-Host "Opening ViSpec console at http://127.0.0.1:8765"
Write-Host "Keep this window open while an experiment is running."
& $VenvPython web\app.py
