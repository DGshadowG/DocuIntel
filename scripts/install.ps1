# Installation script - Sistema Inteligente de Gestion y Analisis Documental
# Creates the virtualenv, installs backend + frontend dependencies, applies
# migrations, seeds initial data and generates the sample corpus.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\install.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== 1/6 Verificando requisitos ===" -ForegroundColor Cyan
python --version
node --version
npm --version

Write-Host "=== 2/6 Entorno virtual de Python ===" -ForegroundColor Cyan
if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip -q
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt -q

Write-Host "=== 3/6 Archivo .env ===" -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Se creo .env desde .env.example - REVISE Y CAMBIE SECRET_KEY y contrasenas" -ForegroundColor Yellow
} else {
    Write-Host ".env ya existe, no se modifica"
}

Write-Host "=== 4/6 Migraciones y seed ===" -ForegroundColor Cyan
Set-Location backend
& ..\.venv\Scripts\python.exe -m alembic upgrade head
& ..\.venv\Scripts\python.exe -m app.db.init_db
Set-Location $Root

Write-Host "=== 5/6 Corpus de 30 documentos ===" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe scripts\generate_corpus.py

Write-Host "=== 6/6 Dependencias del frontend ===" -ForegroundColor Cyan
Set-Location frontend
npm install --no-fund --no-audit
Set-Location $Root

Write-Host ""
Write-Host "Instalacion completa." -ForegroundColor Green
Write-Host "Inicie el sistema con:  powershell -ExecutionPolicy Bypass -File scripts\start.ps1"
