# Build Lambda package - Worker Function (mismo código que main, pero handler diferente)
Write-Host "Building Worker Lambda package..." -ForegroundColor Green

# Clean
Remove-Item -Recurse -Force lambda_package -ErrorAction SilentlyContinue
Remove-Item -Force lambda_worker.zip -ErrorAction SilentlyContinue

# Create temp directory
New-Item -ItemType Directory -Force -Path lambda_package | Out-Null

# Install dependencies using Docker (sin pandas, igual que main)
Write-Host "Installing dependencies using Docker..." -ForegroundColor Yellow
$currentPath = (Get-Location).Path
$lambdaPackagePath = Join-Path $currentPath "lambda_package"
$requirementsPath = Join-Path $currentPath "requirements-main.txt"

# Convert Windows path to Docker volume format (lowercase drive letter)
$dockerOutputPath = $lambdaPackagePath.ToLower().Replace('\', '/').Replace('c:', '/c')
$dockerReqPath = $requirementsPath.ToLower().Replace('\', '/').Replace('c:', '/c')

docker run --rm --entrypoint "" `
    -v "${dockerOutputPath}:/output" `
    -v "${dockerReqPath}:/tmp/requirements.txt" `
    public.ecr.aws/lambda/python:3.11 `
    pip install -r /tmp/requirements.txt -t /output --no-cache-dir

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker install failed, falling back to local pip..." -ForegroundColor Yellow
    pip install -r requirements-main.txt -t lambda_package --platform manylinux2014_x86_64 --only-binary=:all: --upgrade --no-cache-dir
}

# Copy application code
Write-Host "Copying application code..." -ForegroundColor Yellow
Copy-Item -Recurse app lambda_package\
Copy-Item lambda_worker.py lambda_package\

# Clean unnecessary files
Write-Host "Cleaning..." -ForegroundColor Yellow
Set-Location lambda_package
Get-ChildItem -Recurse -Include "__pycache__","*.pyc","*.pyo","*.dist-info\RECORD","*.dist-info\WHEEL" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "^tests?$" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Create ZIP
Write-Host "Creating ZIP..." -ForegroundColor Yellow
Set-Location ..
Compress-Archive -Path lambda_package\* -DestinationPath lambda_worker.zip -Force
Remove-Item -Recurse -Force lambda_package

$size = [math]::Round((Get-Item lambda_worker.zip).Length / 1MB, 2)
Write-Host "Package created: lambda_worker.zip ($size MB)" -ForegroundColor Green
