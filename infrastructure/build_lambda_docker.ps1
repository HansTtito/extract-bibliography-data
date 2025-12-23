# Script para construir Lambda package usando Docker
# Garantiza compatibilidad 100% con AWS Lambda

Write-Host "`n🐳 Construyendo Lambda package con Docker..." -ForegroundColor Cyan

# Verificar que Docker está corriendo
$dockerRunning = docker ps 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker no está corriendo. Por favor inicia Docker Desktop." -ForegroundColor Red
    Write-Host "   Luego ejecuta este script nuevamente." -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Docker está corriendo" -ForegroundColor Green

# Limpiar builds anteriores
if (Test-Path "lambda_package") { Remove-Item -Recurse -Force lambda_package }
if (Test-Path "lambda_function.zip") { Remove-Item -Force lambda_function.zip }

# Crear directorio temporal
New-Item -ItemType Directory -Force -Path lambda_package | Out-Null

Write-Host "`n📦 Paso 1: Instalando dependencias con imagen oficial de Lambda..." -ForegroundColor Yellow
# Usar la imagen oficial de AWS Lambda para Python 3.11
docker run --rm `
    -v "${PWD}/lambda_package:/var/task" `
    -v "${PWD}/requirements.txt:/tmp/requirements.txt" `
    public.ecr.aws/lambda/python:3.11 `
    pip install -r /tmp/requirements.txt -t /var/task --no-cache-dir

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error instalando dependencias" -ForegroundColor Red
    exit 1
}

Write-Host "`n📁 Paso 2: Copiando código de la aplicación..." -ForegroundColor Yellow
Copy-Item -Recurse app lambda_package\
Copy-Item lambda_handler.py lambda_package\

Write-Host "`n🧹 Paso 3: Limpiando archivos innecesarios..." -ForegroundColor Yellow
Set-Location lambda_package

# Eliminar cache y archivos compilados
Get-ChildItem -Recurse -Include "__pycache__","*.pyc","*.pyo","*.pyd" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Eliminar metadata
Get-ChildItem -Recurse -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "\.(dist-info|egg-info)$" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Eliminar tests
Get-ChildItem -Recurse -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "^(tests?|test_|docs?|doc_)$" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Eliminar archivos de documentación
Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue | Where-Object { 
    $_.Extension -match "^(\.md|\.txt|\.rst)$" -or 
    $_.Name -match "^(LICENSE|CHANGELOG|README)" 
} | Remove-Item -Force -ErrorAction SilentlyContinue

# Optimizar pandas y numpy
if (Test-Path "pandas\tests") { Remove-Item -Recurse -Force "pandas\tests" -ErrorAction SilentlyContinue }
if (Test-Path "numpy\tests") { Remove-Item -Recurse -Force "numpy\tests" -ErrorAction SilentlyContinue }
Get-ChildItem -Recurse -Include "*.pyi","*.h","*.hpp","*.c","*.cpp" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "`n📦 Paso 4: Creando archivo ZIP..." -ForegroundColor Yellow
Set-Location ..
Compress-Archive -Path lambda_package\* -DestinationPath lambda_function.zip -Force

# Limpiar
Remove-Item -Recurse -Force lambda_package

# Mostrar resultados
$zipSize = (Get-Item lambda_function.zip).Length / 1MB
Write-Host "`n✅ Package creado exitosamente!" -ForegroundColor Green
Write-Host "   Archivo: lambda_function.zip" -ForegroundColor White
Write-Host "   Tamaño comprimido: $([math]::Round($zipSize, 2)) MB" -ForegroundColor White

# Verificar tamaño descomprimido
Write-Host "`n🔍 Verificando tamaño descomprimido..." -ForegroundColor Yellow
if (Test-Path "temp_check") { Remove-Item -Recurse -Force "temp_check" }
Expand-Archive -Path "lambda_function.zip" -DestinationPath "temp_check" -Force
$unzipSize = (Get-ChildItem -Path "temp_check" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Remove-Item -Recurse -Force "temp_check"

Write-Host "   Tamaño descomprimido: $([math]::Round($unzipSize, 2)) MB" -ForegroundColor White
Write-Host "   Límite Lambda: 250 MB" -ForegroundColor Yellow

if ($unzipSize -lt 250) {
    Write-Host "`n[OK] Package esta dentro del limite de Lambda!" -ForegroundColor Green
    Write-Host "`nProximo paso:" -ForegroundColor Cyan
    Write-Host "   cd infrastructure\terraform" -ForegroundColor White
    Write-Host "   terraform apply -auto-approve" -ForegroundColor White
} else {
    Write-Host "`n[WARN] Package excede el limite de Lambda" -ForegroundColor Red
}

