# Script PowerShell para construir el package de Lambda usando AWS SAM
# Uso: .\build_lambda_sam.ps1

Write-Host "Construyendo package para Lambda con AWS SAM..." -ForegroundColor Green

# Limpiar build anterior si existe
if (Test-Path "lambda_package") {
    Remove-Item -Recurse -Force lambda_package
}
if (Test-Path "lambda_function.zip") {
    Remove-Item -Force lambda_function.zip
}
if (Test-Path ".aws-sam") {
    Remove-Item -Recurse -Force .aws-sam
}

# Crear template.yaml temporal para SAM
$templateContent = @"
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  BibliografiaFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: .
      Handler: lambda_handler.handler
      Runtime: python3.11
      Architectures:
        - x86_64
"@

Set-Content -Path "template.yaml" -Value $templateContent

Write-Host "Ejecutando SAM build..." -ForegroundColor Yellow
sam build --use-container

if ($LASTEXITCODE -eq 0) {
    Write-Host "Copiando código de la aplicación..." -ForegroundColor Yellow
    Copy-Item -Recurse app .aws-sam\build\BibliografiaFunction\
    Copy-Item lambda_handler.py .aws-sam\build\BibliografiaFunction\
    
    Write-Host "Limpiando archivos innecesarios..." -ForegroundColor Yellow
    Set-Location .aws-sam\build\BibliografiaFunction
    
    # Eliminar archivos innecesarios
    Get-ChildItem -Recurse -Include "__pycache__","*.pyc","*.pyo","*.pyd" | Remove-Item -Recurse -Force
    Get-ChildItem -Recurse -Directory | Where-Object { $_.Name -match "\.(dist-info|egg-info)$" } | Remove-Item -Recurse -Force
    Get-ChildItem -Recurse -Directory | Where-Object { $_.Name -match "^(tests?|test_|docs?|doc_|\.tests)$" } | Remove-Item -Recurse -Force
    Get-ChildItem -Recurse -File | Where-Object { $_.Extension -match "^(\.md|\.txt|\.rst)$" -or $_.Name -match "^(LICENSE|CHANGELOG|setup\.py|README)" } | Remove-Item -Force
    Get-ChildItem -Recurse -Include "*.so.dbg","*.pdb" | Remove-Item -Force
    
    # Limpieza agresiva para pandas/numpy
    if (Test-Path "pandas\tests") { Remove-Item -Recurse -Force "pandas\tests" }
    if (Test-Path "pandas\_testing") { Remove-Item -Recurse -Force "pandas\_testing" }
    if (Test-Path "numpy\tests") { Remove-Item -Recurse -Force "numpy\tests" }
    if (Test-Path "numpy\testing\_private") { Remove-Item -Recurse -Force "numpy\testing\_private" }
    Get-ChildItem -Recurse -Include "*.pyi" | Remove-Item -Force
    Get-ChildItem -Recurse -Include "*.h","*.hpp","*.c","*.cpp" | Remove-Item -Force
    
    # Crear ZIP
    Write-Host "Creando archivo ZIP..." -ForegroundColor Yellow
    Set-Location ..\..\..
    Compress-Archive -Path .aws-sam\build\BibliografiaFunction\* -DestinationPath lambda_function.zip -Force
    
    # Limpiar
    Remove-Item -Recurse -Force .aws-sam
    Remove-Item -Force template.yaml
    
    $zipSize = (Get-Item lambda_function.zip).Length / 1MB
    Write-Host "`n✅ Package creado: lambda_function.zip ($([math]::Round($zipSize, 2)) MB)" -ForegroundColor Green
    Write-Host "⚠️  Nota: Lambda tiene un límite de 250MB descomprimido" -ForegroundColor Yellow
} else {
    Write-Host "`n❌ Error en SAM build" -ForegroundColor Red
    Remove-Item -Force template.yaml -ErrorAction SilentlyContinue
}

