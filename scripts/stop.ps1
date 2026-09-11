# Stop script - terminates uvicorn (backend) and vite (frontend) processes.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\stop.ps1

Write-Host "Deteniendo backend (uvicorn) y frontend (vite)..." -ForegroundColor Cyan

Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -match "uvicorn app\.main:app" -or $_.CommandLine -match "vite" } |
    ForEach-Object {
        Write-Host "  Terminando PID $($_.ProcessId): $($_.Name)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

Write-Host "Listo." -ForegroundColor Green
