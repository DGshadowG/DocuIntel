# Backup script - copies the SQLite database and the file storage into a
# timestamped zip under backups\.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\backup.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupDir = Join-Path $Root "backups"
$Target = Join-Path $BackupDir "docuintel-backup-$Stamp"

New-Item -ItemType Directory -Force -Path $Target | Out-Null

# Database (SQLite by default; for PostgreSQL use pg_dump - see manual tecnico)
$Db = Join-Path $Root "database\docuintel.db"
if (Test-Path $Db) {
    Copy-Item $Db (Join-Path $Target "docuintel.db")
    Write-Host "Base de datos copiada"
} else {
    Write-Host "ADVERTENCIA: no se encontro database\docuintel.db" -ForegroundColor Yellow
}

# File storage
$Storage = Join-Path $Root "storage"
if (Test-Path $Storage) {
    Copy-Item $Storage (Join-Path $Target "storage") -Recurse
    Write-Host "Almacenamiento de archivos copiado"
}

Compress-Archive -Path "$Target\*" -DestinationPath "$Target.zip" -Force
Remove-Item $Target -Recurse -Force

Write-Host "Respaldo creado: $Target.zip" -ForegroundColor Green
