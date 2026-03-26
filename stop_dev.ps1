$ErrorActionPreference = "SilentlyContinue"

Write-Host "Stopping Analyst Arena dev servers..." -ForegroundColor Cyan

# Stop uvicorn backend started with api_server:app
$uvicorn = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match "python|uvicorn" -and $_.CommandLine -match "api_server:app"
}
foreach ($p in $uvicorn) {
  Stop-Process -Id $p.ProcessId -Force
  Write-Host "Stopped backend process PID $($p.ProcessId)" -ForegroundColor Green
}

# Stop Vite frontend processes
$vite = Get-CimInstance Win32_Process | Where-Object {
  ($_.Name -match "node|npm") -and ($_.CommandLine -match "vite" -or $_.CommandLine -match "npm run dev")
}
foreach ($p in $vite) {
  Stop-Process -Id $p.ProcessId -Force
  Write-Host "Stopped frontend process PID $($p.ProcessId)" -ForegroundColor Green
}

if (-not $uvicorn -and -not $vite) {
  Write-Host "No matching dev processes found." -ForegroundColor Yellow
} else {
  Write-Host "Done." -ForegroundColor Cyan
}
