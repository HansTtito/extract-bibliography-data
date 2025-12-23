# Despliegue Rápido en AWS (Sin Terraform)

Guía rápida para desplegar usando **CloudFormation** (no necesitas instalar nada extra).

## ¿Por qué CloudFormation?

- ✅ **No necesitas instalar Terraform**
- ✅ **Solo necesitas AWS CLI** (que probablemente ya tienes)
- ✅ **Más simple** para empezar
- ✅ **Nativo de AWS**

## Requisitos

1. **AWS CLI instalado y configurado**
   ```powershell
   aws --version
   aws configure
   ```

2. **Python 3.11+** y dependencias

## Paso 1: Construir Lambda Package

```powershell
.\infrastructure\build_lambda.ps1
```

Esto crea `lambda_function.zip`.

## Paso 2: Desplegar

```powershell
.\infrastructure\scripts\deploy_cloudformation.ps1 -Environment sandbox -GrobidType ec2
```

El script:
1. ✅ Verifica AWS CLI y credenciales
2. ✅ Construye el package de Lambda
3. ✅ Sube el código a S3
4. ✅ Despliega todo con CloudFormation

## Paso 3: Actualizar Lambda con Código Real

Después del despliegue inicial, actualiza la función Lambda:

```powershell
aws lambda update-function-code `
  --function-name bibliografia-stack-function `
  --zip-file fileb://lambda_function.zip
```

## Verificar

```powershell
# Ver outputs
aws cloudformation describe-stacks `
  --stack-name bibliografia-stack `
  --query "Stacks[0].Outputs"

# Probar API
$apiUrl = aws cloudformation describe-stacks `
  --stack-name bibliografia-stack `
  --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" `
  --output text

Invoke-WebRequest -Uri "$apiUrl/health"
```

## Alternativa: Instalar Terraform Manualmente

Si prefieres Terraform:

1. **Descargar Terraform:**
   - Ir a: https://www.terraform.io/downloads
   - Descargar para Windows (64-bit)
   - Extraer el .exe a una carpeta (ej: `C:\terraform`)

2. **Agregar a PATH:**
   - Agregar la carpeta al PATH de Windows
   - O usar desde la carpeta directamente

3. **Verificar:**
   ```powershell
   terraform version
   ```

4. **Usar el script de Terraform:**
   ```powershell
   .\infrastructure\scripts\deploy_aws.ps1 -Environment sandbox -GrobidType ec2
   ```

## Recomendación

**Para empezar rápido: Usa CloudFormation** (no necesitas instalar nada).

¿Quieres probar con CloudFormation ahora?


