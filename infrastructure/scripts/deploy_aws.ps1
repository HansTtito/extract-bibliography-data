# Script PowerShell para desplegar la aplicacion completa en AWS

param(
    [string]$Environment = "sandbox",
    [string]$GrobidType = "ec2",
    [string]$AwsRegion = "us-east-1"
)

Write-Host "Desplegando aplicacion en AWS" -ForegroundColor Cyan
Write-Host "   Ambiente: $Environment"
Write-Host "   GROBID: $GrobidType"
Write-Host "   Region: $AwsRegion"
Write-Host ""

# Verificar requisitos
Write-Host "Verificando requisitos..." -ForegroundColor Yellow
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: AWS CLI no esta instalado" -ForegroundColor Red
    exit 1
}
if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Terraform no esta instalado" -ForegroundColor Red
    exit 1
}

# Verificar credenciales de AWS
Write-Host "Verificando credenciales de AWS..." -ForegroundColor Yellow
try {
    aws sts get-caller-identity | Out-Null
    Write-Host "OK: Credenciales configuradas" -ForegroundColor Green
} catch {
    Write-Host "ERROR: AWS credentials no configuradas" -ForegroundColor Red
    Write-Host "Ejecuta: aws configure" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Construir package de Lambda
Write-Host "Construyendo package de Lambda..." -ForegroundColor Yellow
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptPath)
Set-Location $projectRoot

# Ejecutar build script de Lambda
if (Test-Path "infrastructure\build_lambda.ps1") {
    & "infrastructure\build_lambda.ps1"
} else {
    Write-Host "Creando package manualmente..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path "lambda_package" | Out-Null
    Set-Location "lambda_package"
    pip install -r ..\requirements.txt -t .
    Copy-Item -Recurse ..\app .
    Copy-Item ..\lambda_handler.py .
    Set-Location ..
    Compress-Archive -Path "lambda_package\*" -DestinationPath "lambda_function.zip" -Force
    Remove-Item -Recurse -Force "lambda_package"
}
Write-Host "OK: Package de Lambda creado" -ForegroundColor Green
Write-Host ""

# Inicializar Terraform
Write-Host "Inicializando Terraform..." -ForegroundColor Yellow
Set-Location "infrastructure\terraform"
terraform init
Write-Host ""

# Aplicar configuracion
Write-Host "Aplicando configuracion de Terraform..." -ForegroundColor Yellow
terraform apply `
  -var="environment=$Environment" `
  -var="grobid_deployment=$GrobidType" `
  -var="aws_region=$AwsRegion" `
  -auto-approve

Write-Host ""
Write-Host "Despliegue completado!" -ForegroundColor Green
Write-Host ""
Write-Host "URLs importantes:" -ForegroundColor Cyan
$apiUrl = terraform output -raw api_gateway_url
$frontendUrl = terraform output -raw frontend_url
$grobidUrl = terraform output -raw grobid_url

Write-Host "   API Gateway: $apiUrl"
Write-Host "   Frontend: https://$frontendUrl"
Write-Host "   GROBID: $grobidUrl"

Write-Host ""
Write-Host "Proximos pasos:" -ForegroundColor Yellow
$frontendBucket = terraform output -raw frontend_bucket
Write-Host "   1. Subir frontend: aws s3 sync frontend/ s3://$frontendBucket"
Write-Host "   2. Probar la API desde el navegador o con curl"
