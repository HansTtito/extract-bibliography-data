# Build Lambda package - Main Function (sin pandas)
Write-Host "Building Main Lambda package (without pandas)..." -ForegroundColor Green

# Clean
Remove-Item -Recurse -Force lambda_package -ErrorAction SilentlyContinue
Remove-Item -Force lambda_function.zip -ErrorAction SilentlyContinue

# Create temp directory
New-Item -ItemType Directory -Force -Path lambda_package | Out-Null

# Install dependencies using Docker
Write-Host "Installing dependencies using Docker..." -ForegroundColor Yellow
$currentPath = (Get-Location).Path.Replace('\', '/')
docker run --rm --entrypoint "" `
    -v "$($currentPath)/lambda_package:/output" `
    -v "$($currentPath)/requirements.txt:/tmp/requirements.txt" `
    public.ecr.aws/lambda/python:3.11 `
    pip install -r /tmp/requirements.txt -t /output --no-cache-dir

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker install failed, falling back to local pip..." -ForegroundColor Yellow
    pip install -r requirements.txt -t lambda_package --platform manylinux2014_x86_64 --only-binary=:all: --upgrade --no-cache-dir
}

# Copy application code
Write-Host "Copying application code..." -ForegroundColor Yellow
Copy-Item -Recurse app lambda_package\
Copy-Item lambda_handler.py lambda_package\

# Clean unnecessary files
Write-Host "Cleaning..." -ForegroundColor Yellow
Set-Location lambda_package
Get-ChildItem -Recurse -Include "__pycache__","*.pyc","*.pyo","*.dist-info\RECORD","*.dist-info\WHEEL" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "^tests?$" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Create ZIP
Write-Host "Creating ZIP..." -ForegroundColor Yellow
Set-Location ..
Compress-Archive -Path lambda_package\* -DestinationPath lambda_function.zip -Force
Remove-Item -Recurse -Force lambda_package

$size = [math]::Round((Get-Item lambda_function.zip).Length / 1MB, 2)
Write-Host "Package created: lambda_function.zip ($size MB)" -ForegroundColor Green

