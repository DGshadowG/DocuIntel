# Restore script - restores database and storage from a backup zip.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\restore.ps1 -BackupZip backups\docuintel-backup-XXXX.zip
param(
    [Parameter(Mandatory = $true)]
    [string]$BackupZip
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path $BackupZip)) {
    Write-Host "ERROR: no existe el archivo $BackupZip" -ForegroundColor Red
    exit 1
}

Write-Host "IMPORTANTE: detenga la aplicacion antes de restaurar (scripts\stop.ps1)" -ForegroundColor Yellow
$confirm = Read-Host "Se SOBREESCRIBIRAN la base de datos y el almacenamiento actuales. Escriba SI para continuar"
if ($confirm -ne "SI") {
    Write-Host "Restauracion cancelada"
    exit 0
}

$Temp = Join-Path $env:TEMP "docuintel-restore"
if (Test-Path $Temp) { Remove-Item $Temp -Recurse -Force }
Expand-Archive -Path $BackupZip -DestinationPath $Temp

$DbSrc = Join-Path $Temp "docuintel.db"
if (Test-Path $DbSrc) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root "database") | Out-Null
    Copy-Item $DbSrc (Join-Path $Root "database\docuintel.db") -Force
    Write-Host "Base de datos restaurada"
}

$StorageSrc = Join-Path $Temp "storage"
if (Test-Path $StorageSrc) {
    $StorageDst = Join-Path $Root "storage"
    if (Test-Path $StorageDst) { Remove-Item $StorageDst -Recurse -Force }
    Copy-Item $StorageSrc $StorageDst -Recurse
    Write-Host "Almacenamiento restaurado"
}

Remove-Item $Temp -Recurse -Force
Write-Host "Restauracion completa. Inicie la aplicacion con scripts\start.ps1" -ForegroundColor Green
