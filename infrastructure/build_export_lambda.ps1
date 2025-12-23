# Build Lambda package - Export Function (con pandas)
Write-Host "Building Export Lambda package (with pandas)..." -ForegroundColor Green

# Clean
Remove-Item -Recurse -Force lambda_package_export -ErrorAction SilentlyContinue
Remove-Item -Force lambda_function_export.zip -ErrorAction SilentlyContinue

# Create temp directory
New-Item -ItemType Directory -Force -Path lambda_package_export | Out-Null

# Install dependencies using local pip (fallback)
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements-export.txt -t lambda_package_export --platform manylinux2014_x86_64 --only-binary=:all: --upgrade --no-cache-dir

# Copy application code (solo lo necesario para exports)
Write-Host "Copying application code..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path lambda_package_export\app | Out-Null
Copy-Item app\__init__.py lambda_package_export\app\
Copy-Item app\config.py lambda_package_export\app\
Copy-Item app\database.py lambda_package_export\app\
Copy-Item app\models.py lambda_package_export\app\
Copy-Item app\schemas.py lambda_package_export\app\
Copy-Item app\main_export.py lambda_package_export\app\

New-Item -ItemType Directory -Force -Path lambda_package_export\app\routers | Out-Null
Copy-Item app\routers\__init__.py lambda_package_export\app\routers\
Copy-Item app\routers\download.py lambda_package_export\app\routers\

New-Item -ItemType Directory -Force -Path lambda_package_export\app\services | Out-Null
Copy-Item app\services\__init__.py lambda_package_export\app\services\
Copy-Item app\services\export_service.py lambda_package_export\app\services\

Copy-Item lambda_handler_export.py lambda_package_export\

# Clean unnecessary files
Write-Host "Cleaning..." -ForegroundColor Yellow
Set-Location lambda_package_export
Get-ChildItem -Recurse -Include "__pycache__","*.pyc","*.pyo","*.dist-info\RECORD","*.dist-info\WHEEL" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "^tests?$" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
if (Test-Path "pandas\tests") { Remove-Item -Recurse -Force "pandas\tests" -ErrorAction SilentlyContinue }
if (Test-Path "numpy\tests") { Remove-Item -Recurse -Force "numpy\tests" -ErrorAction SilentlyContinue }

# Create ZIP
Write-Host "Creating ZIP..." -ForegroundColor Yellow
Set-Location ..
Compress-Archive -Path lambda_package_export\* -DestinationPath lambda_function_export.zip -Force
Remove-Item -Recurse -Force lambda_package_export

$size = [math]::Round((Get-Item lambda_function_export.zip).Length / 1MB, 2)
Write-Host "Package created: lambda_function_export.zip ($size MB)" -ForegroundColor Green

