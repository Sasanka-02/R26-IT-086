# SpeakFree - start the complete platform (Components 1-4) on localhost.
#   Double-click start-speakfree.bat, or run:  powershell -ExecutionPolicy Bypass -File start-speakfree.ps1
# First run installs everything (Python venv + packages, npm packages) - this takes a while.
# Website: http://localhost:5173      API docs: http://localhost:8000/docs

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "speakfree-component1\backend"
$Frontend = Join-Path $Root "speakfree-component1\frontend"
$Python = Join-Path $Backend "venv\Scripts\python.exe"

function Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }

# ---------------------------------------------------------------- prerequisites
Step "Checking prerequisites"
if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.11 is not installed. Install it from python.org (tick 'Add to PATH')."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "Node.js is not installed. Install Node 20+ from nodejs.org." }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "WARNING: FFmpeg was not found on PATH - recordings cannot be analysed. Install with: winget install Gyan.FFmpeg" -ForegroundColor Yellow
}

# ---------------------------------------------------------------- backend
if (-not (Test-Path $Python)) {
    Step "Creating the Python environment (first run)"
    Push-Location $Backend
    if (Get-Command py -ErrorAction SilentlyContinue) { py -3.11 -m venv venv } else { python -m venv venv }
    & $Python -m pip install --upgrade pip
    & $Python -m pip install -r requirements.txt
    Pop-Location
}
if (-not (Test-Path (Join-Path $Backend ".env"))) {
    Copy-Item (Join-Path $Backend ".env.example") (Join-Path $Backend ".env")
    $secret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
    (Get-Content (Join-Path $Backend ".env")) -replace "^JWT_SECRET=.*", "JWT_SECRET=$secret" | Set-Content (Join-Path $Backend ".env") -Encoding ascii
}

Step "Preparing the database (migrations, task library, pipeline backfill)"
Push-Location $Backend
& $Python -m alembic upgrade head
& $Python seed.py
& $Python tools\backfill_pipeline.py
Pop-Location

# ---------------------------------------------------------------- frontend
if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Step "Installing website packages (first run)"
    Push-Location $Frontend; npm install; Pop-Location
}
if (-not (Test-Path (Join-Path $Frontend ".env"))) { Copy-Item (Join-Path $Frontend ".env.example") (Join-Path $Frontend ".env") }

# ---------------------------------------------------------------- start servers (each in its own window)
Step "Starting the backend (port 8000) and the website (port 5173)"
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle='SpeakFree backend'; Set-Location '$Backend'; & '$Python' -m uvicorn main:app --host 127.0.0.1 --port 8000 --timeout-graceful-shutdown 3"
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle='SpeakFree website'; Set-Location '$Frontend'; npm run dev"

Step "Waiting for the backend"
$ok = $false
for ($i = 0; $i -lt 90; $i++) {
    try { Invoke-RestMethod "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 2 | Out-Null; $ok = $true; break } catch { Start-Sleep -Seconds 1 }
}
if (-not $ok) { throw "The backend did not start - check the 'SpeakFree backend' window." }

Step "Loading the speech models in the background (Whisper + Component 3 models)"
# separate hidden process, so it keeps running after this script ends (first run also downloads Whisper, ~140 MB)
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile", "-Command",
    "try { Invoke-RestMethod -Method Post 'http://127.0.0.1:8000/api/v1/system/warmup' -TimeoutSec 900 | Out-Null } catch {}"

for ($i = 0; $i -lt 60; $i++) {
    try { Invoke-WebRequest "http://localhost:5173" -UseBasicParsing -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep -Seconds 1 }
}
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "SpeakFree is running." -ForegroundColor Green
Write-Host "  Website   : http://localhost:5173"
Write-Host "  API docs  : http://localhost:8000/docs"
Write-Host "  Admin     : admin@speakfree.lk / SpeakFree@Admin2026"
Write-Host "  Stop      : run stop-speakfree.bat (or close the two server windows)"
