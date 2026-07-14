$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

Set-Location $RepoRoot

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating local Python environment..."
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv .venv
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv .venv
    } else {
        throw "Python 3 is not installed or not available in PATH."
    }
}

Write-Host "Installing web console dependencies..."
& $VenvPython -m pip install -r requirements-web.txt
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed. Check the network and rerun this script."
}

Write-Host "Web console environment is ready."
