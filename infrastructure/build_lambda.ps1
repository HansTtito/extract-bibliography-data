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

Write-Host "Instalando dependencias para Linux (Lambda)..." -ForegroundColor Yellow
# Instalar dependencias para Linux (Lambda usa Amazon Linux 2)
# Nota: Instalamos para Windows pero funcionará en Lambda (binarios compatibles)
pip install -r ..\requirements.txt -t . --upgrade --quiet

# Verificar que pydantic_core está instalado correctamente
Write-Host "Verificando pydantic_core..." -ForegroundColor Yellow
if (-not (Test-Path "pydantic_core")) {
    Write-Host "  Reinstalando pydantic con dependencias..." -ForegroundColor Yellow
    pip install --force-reinstall --no-cache-dir pydantic==2.5.0 -t . --quiet
}

Write-Host "Copiando código de la aplicación..." -ForegroundColor Yellow
# Copiar código de la aplicación
Copy-Item -Recurse ..\app .
Copy-Item ..\lambda_handler.py .

Write-Host "Limpiando archivos innecesarios..." -ForegroundColor Yellow
# Eliminar archivos innecesarios para reducir tamaño
Get-ChildItem -Recurse -Include "__pycache__","*.pyc","*.pyo","*.pyd" | Remove-Item -Recurse -Force
# Eliminar .dist-info y .egg-info (contienen metadata innecesaria)
Get-ChildItem -Recurse -Directory | Where-Object { $_.Name -match "\.(dist-info|egg-info)$" } | Remove-Item -Recurse -Force
# Eliminar tests y docs de paquetes
Get-ChildItem -Recurse -Directory | Where-Object { $_.Name -match "^(tests?|test_|docs?|doc_|\.tests)$" } | Remove-Item -Recurse -Force
# Eliminar archivos de desarrollo
Get-ChildItem -Recurse -File | Where-Object { $_.Extension -match "^(\.md|\.txt|\.rst)$" -or $_.Name -match "^(LICENSE|CHANGELOG|setup\.py|README)" } | Remove-Item -Force
# Eliminar archivos de debug
Get-ChildItem -Recurse -Include "*.so.dbg","*.pdb" | Remove-Item -Force

# Limpieza agresiva para pandas/numpy
Write-Host "Optimizando pandas y numpy..." -ForegroundColor Yellow
# Eliminar tests de pandas
if (Test-Path "pandas\tests") { Remove-Item -Recurse -Force "pandas\tests" }
if (Test-Path "pandas\_testing") { Remove-Item -Recurse -Force "pandas\_testing" }
# Eliminar tests de numpy
if (Test-Path "numpy\tests") { Remove-Item -Recurse -Force "numpy\tests" }
if (Test-Path "numpy\testing\_private") { Remove-Item -Recurse -Force "numpy\testing\_private" }
# Eliminar type stubs (no necesarios en runtime)
Get-ChildItem -Recurse -Include "*.pyi" | Remove-Item -Force
# Eliminar archivos C++ header y source (no necesarios en runtime)
Get-ChildItem -Recurse -Include "*.h","*.hpp","*.c","*.cpp" | Remove-Item -Force
# Eliminar archivos de ejemplo
Get-ChildItem -Recurse -Directory | Where-Object { $_.Name -match "^(example|sample)" } | Remove-Item -Recurse -Force

# Crear ZIP
Write-Host "Creando archivo ZIP..." -ForegroundColor Yellow
Set-Location ..
Compress-Archive -Path lambda_package\* -DestinationPath lambda_function.zip -Force

# Limpiar directorio temporal
Remove-Item -Recurse -Force lambda_package

$zipSize = (Get-Item lambda_function.zip).Length / 1MB
Write-Host "`n✅ Package creado: lambda_function.zip ($([math]::Round($zipSize, 2)) MB)" -ForegroundColor Green
Write-Host "⚠️  Nota: Lambda tiene un límite de 250MB descomprimido" -ForegroundColor Yellow

