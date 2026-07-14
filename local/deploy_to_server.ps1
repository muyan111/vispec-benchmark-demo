param(
    [string]$Port = "2225",
    [string]$Key = "$env:USERPROFILE\.ssh\vispec_codex",
    [string]$RemoteDir = "/home/vispec-benchmark-demo"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Archive = Join-Path $env:TEMP "vispec-benchmark-demo-deploy.tar.gz"
$KnownHosts = "$env:USERPROFILE\.ssh\vispec_node00_known_hosts"

Set-Location $RepoRoot

Write-Host "Packaging the current Git revision..."
git archive --format=tar.gz --output="$Archive" HEAD
if ($LASTEXITCODE -ne 0) { throw "git archive failed" }

Write-Host "Uploading through localhost:$Port..."
ssh -i $Key -p $Port `
    -o BatchMode=yes `
    -o ConnectTimeout=15 `
    -o StrictHostKeyChecking=no `
    -o UserKnownHostsFile=$KnownHosts `
    root@localhost "mkdir -p '$RemoteDir'"
if ($LASTEXITCODE -ne 0) { throw "Remote directory preparation failed" }

scp -O -i $Key -P $Port `
    -o BatchMode=yes `
    -o ConnectTimeout=15 `
    -o StrictHostKeyChecking=no `
    -o UserKnownHostsFile=$KnownHosts `
    "$Archive" "root@localhost:/tmp/vispec-benchmark-demo-deploy.tar.gz"
if ($LASTEXITCODE -ne 0) { throw "Archive upload failed" }

Write-Host "Installing server files..."
ssh -i $Key -p $Port `
    -o BatchMode=yes `
    -o ConnectTimeout=15 `
    -o StrictHostKeyChecking=no `
    -o UserKnownHostsFile=$KnownHosts `
    root@localhost "tar -xzf /tmp/vispec-benchmark-demo-deploy.tar.gz -C '$RemoteDir' && cd '$RemoteDir' && bash server/setup_server.sh"
if ($LASTEXITCODE -ne 0) { throw "Server installation failed" }

Remove-Item -LiteralPath $Archive -Force -ErrorAction SilentlyContinue
Write-Host "A100 deployment completed: $RemoteDir"
