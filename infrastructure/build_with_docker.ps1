# Build Lambda package with Docker
Write-Host "Building Lambda package with Docker..." -ForegroundColor Green

# Clean previous builds
Remove-Item -Recurse -Force lambda_package -ErrorAction SilentlyContinue
Remove-Item -Force lambda_function.zip -ErrorAction SilentlyContinue

# Create temp directory
New-Item -ItemType Directory -Force -Path lambda_package | Out-Null

# Install dependencies using Lambda Docker image
Write-Host "Installing dependencies..." -ForegroundColor Yellow
docker run --rm --entrypoint /bin/bash -v "${PWD}/lambda_package:/var/task" -v "${PWD}/requirements.txt:/tmp/requirements.txt" public.ecr.aws/lambda/python:3.11 -c "pip install -r /tmp/requirements.txt -t /var/task --no-cache-dir"

# Copy application code
Write-Host "Copying application code..." -ForegroundColor Yellow
Copy-Item -Recurse app lambda_package\
Copy-Item lambda_handler.py lambda_package\

# Clean unnecessary files
Write-Host "Cleaning unnecessary files..." -ForegroundColor Yellow
Set-Location lambda_package
Get-ChildItem -Recurse -Include "__pycache__","*.pyc","*.pyo" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "\.dist-info$|\.egg-info$|^tests?$" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
if (Test-Path "pandas\tests") { Remove-Item -Recurse -Force "pandas\tests" }
if (Test-Path "numpy\tests") { Remove-Item -Recurse -Force "numpy\tests" }

# Create ZIP
Write-Host "Creating ZIP file..." -ForegroundColor Yellow
Set-Location ..
Compress-Archive -Path lambda_package\* -DestinationPath lambda_function.zip -Force
Remove-Item -Recurse -Force lambda_package

$size = [math]::Round((Get-Item lambda_function.zip).Length / 1MB, 2)
Write-Host "Package created: lambda_function.zip ($size MB)" -ForegroundColor Green

