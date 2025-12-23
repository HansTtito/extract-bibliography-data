# Fix: Lambda Package Build para Linux

## Problema

Lambda está fallando con:
```
Runtime.ImportModuleError: No module named 'pydantic_core._pydantic_core'
```

Esto ocurre porque el package fue construido en Windows y Lambda necesita binarios para Linux.

## Solución

El script `build_lambda.ps1` ahora usa `--platform manylinux2014_x86_64` para obtener wheels compatibles con Lambda.

## Pasos para Reconstruir

1. **Reconstruir el package:**
   ```powershell
   .\infrastructure\build_lambda.ps1
   ```

2. **Subir el nuevo package a S3 y actualizar Lambda:**
   ```powershell
   cd infrastructure\terraform
   terraform apply -var="environment=sandbox" -var="grobid_deployment=ec2" -var="aws_region=us-east-1" -auto-approve
   ```

## Alternativa: Usar Docker (Más Confiable)

Si el método anterior no funciona, usar Docker:

```powershell
# Construir package usando Docker (Linux)
docker run --rm -v ${PWD}:/var/task public.ecr.aws/lambda/python:3.11 bash -c "pip install -r requirements.txt -t lambda_package && cp -r app lambda_package/ && cp lambda_handler.py lambda_package/ && cd lambda_package && zip -r ../lambda_function.zip ."
```

