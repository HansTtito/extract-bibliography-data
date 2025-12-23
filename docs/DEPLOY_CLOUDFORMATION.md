# Despliegue con CloudFormation (Sin Terraform)

Esta guía te muestra cómo desplegar usando CloudFormation, que es **nativo de AWS** y no requiere instalar Terraform.

## ¿Por qué CloudFormation?

- ✅ **No necesitas instalar nada**: Ya viene con AWS CLI
- ✅ **Nativo de AWS**: Integración 100% con AWS
- ✅ **Más simple**: Menos herramientas que gestionar
- ✅ **Drift detection**: Detecta cambios manuales

## Requisitos

1. **AWS CLI instalado y configurado**
   ```bash
   aws configure
   ```

2. **Python 3.11+** y dependencias

3. **Docker** (para construir Lambda package)

## Paso 1: Construir Lambda Package

```powershell
.\infrastructure\build_lambda.ps1
```

## Paso 2: Desplegar con CloudFormation

### Opción A: Script Automatizado

```powershell
.\infrastructure\scripts\deploy_cloudformation.ps1 -Environment sandbox -GrobidType ec2
```

### Opción B: Manual

```powershell
# 1. Subir código Lambda a S3
aws s3 mb s3://bibliografia-lambda-code
aws s3 cp lambda_function.zip s3://bibliografia-lambda-code/

# 2. Desplegar stack
aws cloudformation deploy `
  --template-file infrastructure/cloudformation/template.yaml `
  --stack-name bibliografia-stack `
  --parameter-overrides Environment=sandbox GrobidDeployment=ec2 `
  --capabilities CAPABILITY_NAMED_IAM
```

## Paso 3: Actualizar Lambda con Código Real

Después de crear el stack, actualiza la función Lambda:

```powershell
aws lambda update-function-code `
  --function-name bibliografia-stack-function `
  --zip-file fileb://lambda_function.zip
```

## Verificar Despliegue

```powershell
# Ver outputs del stack
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

## Actualizar Código

```powershell
# 1. Reconstruir package
.\infrastructure\build_lambda.ps1

# 2. Actualizar Lambda
aws lambda update-function-code `
  --function-name bibliografia-stack-function `
  --zip-file fileb://lambda_function.zip
```

## Destruir Stack

```powershell
aws cloudformation delete-stack --stack-name bibliografia-stack
```

## Comparación con Terraform

| Aspecto | CloudFormation | Terraform |
|---------|----------------|-----------|
| Instalación | No necesaria | Requiere instalación |
| Sintaxis | YAML/JSON | HCL (más legible) |
| Velocidad | Más lento | Más rápido |
| Multi-cloud | No | Sí |
| Para tu caso | ✅ Mejor | También funciona |

## Recomendación

**Para tu proyecto (solo AWS): CloudFormation es más simple** porque no necesitas instalar Terraform.

¿Quieres usar CloudFormation en lugar de Terraform?

