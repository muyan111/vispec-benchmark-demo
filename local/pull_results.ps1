param(
  [string]$Port = "2225",
  [string]$Key = "$env:USERPROFILE\.ssh\vispec_codex",
  [string]$RemoteDir = "/home/vispec_repro/outputs/benchmark_dashboard",
  [string]$LocalDir = "$env:USERPROFILE\Documents\投机采样\outputs\benchmark_dashboard_from_server"
)

New-Item -ItemType Directory -Force -Path $LocalDir | Out-Null

scp -O -P $Port -i $Key root@localhost:${RemoteDir}/metrics_dashboard.png "$LocalDir\metrics_dashboard.png"
scp -O -P $Port -i $Key root@localhost:${RemoteDir}/results.json "$LocalDir\results.json"
scp -O -P $Port -i $Key root@localhost:${RemoteDir}/run.log "$LocalDir\run.log"

Write-Host "Saved to $LocalDir"
Write-Host "Open image:"
Write-Host "  start `"$LocalDir\metrics_dashboard.png`""
