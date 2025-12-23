# Script PowerShell para desplegar con CloudFormation

param(
    [string]$Environment = "sandbox",
    [string]$GrobidType = "ec2",
    [string]$AwsRegion = "us-east-1",
    [string]$StackName = "bibliografia-stack"
)

Write-Host "Desplegando aplicacion en AWS con CloudFormation" -ForegroundColor Cyan
Write-Host "   Stack: $StackName"
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

# Verificar credenciales
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
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $projectRoot

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

# Subir código a S3 para Lambda
Write-Host "Subiendo codigo de Lambda a S3..." -ForegroundColor Yellow
$s3Bucket = "${StackName}-lambda-code-$(Get-Random)"
aws s3 mb "s3://$s3Bucket" --region $AwsRegion 2>$null
aws s3 cp lambda_function.zip "s3://$s3Bucket/lambda_function.zip" --region $AwsRegion
Write-Host "OK: Codigo subido a s3://$s3Bucket" -ForegroundColor Green
Write-Host ""

# Desplegar CloudFormation
Write-Host "Desplegando stack de CloudFormation..." -ForegroundColor Yellow
Set-Location "infrastructure\cloudformation"

aws cloudformation deploy `
  --template-file template.yaml `
  --stack-name $StackName `
  --parameter-overrides `
    Environment=$Environment `
    GrobidDeployment=$GrobidType `
    CrossrefEmail="" `
  --capabilities CAPABILITY_NAMED_IAM `
  --region $AwsRegion

Write-Host ""
Write-Host "Despliegue completado!" -ForegroundColor Green
Write-Host ""
Write-Host "Obteniendo URLs..." -ForegroundColor Cyan

$apiUrl = aws cloudformation describe-stacks `
  --stack-name $StackName `
  --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" `
  --output text `
  --region $AwsRegion

$frontendUrl = aws cloudformation describe-stacks `
  --stack-name $StackName `
  --query "Stacks[0].Outputs[?OutputKey=='FrontendUrl'].OutputValue" `
  --output text `
  --region $AwsRegion

Write-Host "   API Gateway: $apiUrl"
Write-Host "   Frontend: https://$frontendUrl"

