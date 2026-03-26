$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot
$frontendDir = Join-Path $repoRoot "Frontend-figma"
$envFile = Join-Path $repoRoot ".env"

if (-not (Test-Path $frontendDir)) {
  throw "Frontend directory not found at: $frontendDir"
}

if (Test-Path $envFile) {
  Get-Content -LiteralPath $envFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
    $parts = $line.Split("=", 2)
    $key = $parts[0].Trim()
    $value = $parts[1].Trim()
    [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
  }
}

if (-not $env:HUD_API_KEY) {
  Write-Host "Warning: HUD_API_KEY is not set. hud_model will fail." -ForegroundColor Yellow
}
if (-not $env:OPENAI_API_KEY) {
  Write-Host "Warning: OPENAI_API_KEY is not set. gpt4o will fail." -ForegroundColor Yellow
}
if (-not $env:HUD_MODEL) {
  Write-Host "Warning: HUD_MODEL is empty. Set it in .env to your HUD model id." -ForegroundColor Yellow
}

Write-Host "Starting Analyst Arena backend and frontend..." -ForegroundColor Cyan

$backendScript = @"
Set-Location -LiteralPath '$repoRoot'
uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
"@

$frontendScript = @"
Set-Location -LiteralPath '$frontendDir'
`$env:VITE_API_BASE_URL='http://localhost:8000'
if (-not (Test-Path node_modules)) { npm install }
npm run dev
"@

$backendEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($backendScript))
$frontendEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($frontendScript))

Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", $backendEncoded | Out-Null
Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", $frontendEncoded | Out-Null

Write-Host "Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend: http://localhost:4173" -ForegroundColor Green
Write-Host "Two terminals were opened for both services." -ForegroundColor Yellow

Start-Sleep -Seconds 2
Start-Process "http://localhost:4173"
Write-Host "Opened frontend in browser." -ForegroundColor Cyan
