# Script para subir el frontend a S3
# Uso: .\infrastructure\scripts\upload_frontend.ps1

param(
    [string]$Environment = "sandbox",
    [string]$AwsRegion = "us-east-1"
)

Write-Host "Subiendo frontend a S3..." -ForegroundColor Cyan

# Obtener nombre del bucket desde Terraform
$terraformDir = Join-Path $PSScriptRoot "..\terraform"
Set-Location $terraformDir

$bucketName = terraform output -raw frontend_bucket 2>$null

if (-not $bucketName) {
    Write-Host "❌ Error: No se pudo obtener el nombre del bucket" -ForegroundColor Red
    Write-Host "Asegúrate de que Terraform esté desplegado" -ForegroundColor Yellow
    exit 1
}

Write-Host "Bucket: $bucketName" -ForegroundColor Green
Write-Host ""

# Volver al directorio raíz
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $projectRoot

# Verificar que existe la carpeta frontend
if (-not (Test-Path "frontend")) {
    Write-Host "❌ Error: No se encontró la carpeta frontend" -ForegroundColor Red
    exit 1
}

# Subir archivos
Write-Host "Subiendo archivos..." -ForegroundColor Yellow
aws s3 sync frontend/ "s3://$bucketName" `
    --delete `
    --region $AwsRegion `
    --exclude ".git/*" `
    --exclude "*.md"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Frontend subido exitosamente!" -ForegroundColor Green
    Write-Host ""
    Write-Host "URLs:" -ForegroundColor Cyan
    Set-Location $terraformDir
    $frontendUrl = terraform output -raw frontend_url
    Set-Location $projectRoot
    Write-Host "  Frontend: https://$frontendUrl" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "❌ Error al subir el frontend" -ForegroundColor Red
    exit 1
}

