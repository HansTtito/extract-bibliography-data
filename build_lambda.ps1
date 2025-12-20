# Script PowerShell para construir el package de Lambda
# Uso: .\build_lambda.ps1

Write-Host "Construyendo package para Lambda..." -ForegroundColor Green

# Limpiar build anterior si existe
if (Test-Path "lambda_package") {
    Remove-Item -Recurse -Force lambda_package
}
if (Test-Path "lambda_function.zip") {
    Remove-Item -Force lambda_function.zip
}

# Crear directorio temporal
New-Item -ItemType Directory -Force -Path lambda_package | Out-Null
Set-Location lambda_package

Write-Host "Instalando dependencias..." -ForegroundColor Yellow
# Instalar dependencias en el directorio actual
pip install -r ..\requirements.txt -t . --quiet

Write-Host "Copiando código de la aplicación..." -ForegroundColor Yellow
# Copiar código de la aplicación
Copy-Item -Recurse ..\app .
Copy-Item ..\lambda_handler.py .

# Crear ZIP
Write-Host "Creando archivo ZIP..." -ForegroundColor Yellow
Set-Location ..
Compress-Archive -Path lambda_package\* -DestinationPath lambda_function.zip -Force

# Limpiar directorio temporal
Remove-Item -Recurse -Force lambda_package

$zipSize = (Get-Item lambda_function.zip).Length / 1MB
Write-Host "`n✅ Package creado: lambda_function.zip ($([math]::Round($zipSize, 2)) MB)" -ForegroundColor Green
Write-Host "⚠️  Nota: Lambda tiene un límite de 250MB descomprimido" -ForegroundColor Yellow

