# Start script - launches backend (uvicorn, embedded worker) and frontend (vite)
# in two PowerShell windows.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\start.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "Iniciando backend en http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$Root\backend'; & '$Root\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
)

Write-Host "Iniciando frontend en http://localhost:5173 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$Root\frontend'; npm run dev"
)

Start-Sleep -Seconds 5
try {
    $health = Invoke-RestMethod "http://localhost:8000/health"
    Write-Host "Backend: $($health.status) (BD: $($health.database), IA: $($health.ai_provider))" -ForegroundColor Green
} catch {
    Write-Host "El backend aun esta arrancando; verifique en unos segundos." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Aplicacion:      http://localhost:5173" -ForegroundColor Green
Write-Host "API / Swagger:   http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host "Para cargar el corpus demo: .\.venv\Scripts\python.exe scripts\load_corpus.py"
