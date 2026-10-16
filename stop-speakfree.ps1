# SpeakFree - stop the backend (uvicorn on port 8000) and the website (vite) started by start-speakfree.ps1.
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Frontend = Join-Path $Root "speakfree-component1\frontend"

foreach ($port in 8000, 5173) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        $p = Get-CimInstance Win32_Process -Filter "ProcessId=$($c.OwningProcess)"
        if ($p -and ($p.CommandLine -like "*uvicorn*" -or $p.CommandLine -like "*vite*" -or $p.ExecutablePath -like "$Frontend*")) {
            Stop-Process -Id $p.ProcessId -Force
            Write-Host "Stopped $($p.Name) on port $port"
        }
    }
}
Write-Host "SpeakFree stopped. You can close the server windows."
