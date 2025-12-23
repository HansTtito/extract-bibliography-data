# Guía de Despliegue en AWS Lambda (Serverless)

Esta guía te ayudará a desplegar tu aplicación en AWS Lambda, ideal para **uso esporádico** (unas cuantas veces al mes).

## ¿Por qué Lambda para tu caso?

- ✅ **Costo mínimo**: Solo pagas cuando se usa (~$0.20 por 1M requests)
- ✅ **Sin costos fijos**: No pagas $47/mes por un servidor que casi no usas
- ✅ **Escalado automático**: Listo cuando lo necesites
- ✅ **Ideal para uso esporádico**: Perfecto si solo usas la app unas veces al mes

**Costo estimado con uso esporádico:**
- 10-50 requests/mes: ~$1-5/mes (vs $47/mes de EC2)
- **Ahorro: ~$42-46/mes** 💰

---

## Arquitectura Serverless

```
API Gateway
  └── Lambda Function (FastAPI)
      ├── /upload-pdf
      ├── /upload-reference
      ├── /upload-references-pdf
      └── /api/* (otros endpoints)
  └── RDS PostgreSQL (db.t3.micro)
  └── S3 + CloudFront (Frontend estático)
```

---

## Requisitos Previos

1. **Cuenta de AWS** (con permisos para crear recursos)
2. **AWS CLI instalado y configurado**
3. **Python 3.11+** localmente
4. **Docker** (para construir el package de Lambda)

---

## Paso 1: Preparar el Código para Lambda

Lambda necesita algunas modificaciones. Vamos a crear una versión adaptada:

### 1.1 Crear handler para Lambda

Crea `lambda_handler.py` en la raíz:

```python
"""
Handler para AWS Lambda
"""
import os
import sys
from mangum import Mangum
from app.main import app

# Configurar para Lambda
os.environ.setdefault("DATABASE_URL", os.getenv("DATABASE_URL"))

# Mangum convierte FastAPI a ASGI para Lambda
handler = Mangum(app, lifespan="off")
```

### 1.2 Actualizar requirements.txt

Agrega `mangum` para conectar FastAPI con Lambda:

```txt
mangum==0.17.0
```

### 1.3 Crear script de build para Lambda

Crea `build_lambda.sh` (o `build_lambda.ps1` para Windows):

```bash
#!/bin/bash
# Script para construir el package de Lambda

echo "Construyendo package para Lambda..."

# Crear directorio temporal
mkdir -p lambda_package
cd lambda_package

# Instalar dependencias en el directorio
pip install -r ../requirements.txt -t .

# Copiar código de la aplicación
cp -r ../app .
cp ../lambda_handler.py .

# Crear ZIP
cd ..
zip -r lambda_function.zip lambda_package/*
rm -rf lambda_package

echo "Package creado: lambda_function.zip"
```

Para Windows PowerShell (`build_lambda.ps1`):

```powershell
# Script para construir el package de Lambda

Write-Host "Construyendo package para Lambda..."

# Crear directorio temporal
New-Item -ItemType Directory -Force -Path lambda_package
Set-Location lambda_package

# Instalar dependencias
pip install -r ..\requirements.txt -t .

# Copiar código
Copy-Item -Recurse ..\app .
Copy-Item ..\lambda_handler.py .

# Crear ZIP
Set-Location ..
Compress-Archive -Path lambda_package\* -DestinationPath lambda_function.zip -Force
Remove-Item -Recurse -Force lambda_package

Write-Host "Package creado: lambda_function.zip"
```

---

## Paso 2: Configurar RDS PostgreSQL

### 2.1 Crear RDS Instance

```bash
aws rds create-db-instance \
  --db-instance-identifier bibliografia-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username admin \
  --master-user-password TuPasswordSeguro123! \
  --allocated-storage 20 \
  --vpc-security-group-ids sg-xxxxx \
  --db-name bibliografia_db \
  --backup-retention-period 7 \
  --publicly-accessible
```

**Nota**: Necesitas crear un Security Group primero que permita conexiones desde Lambda.

### 2.2 Obtener Endpoint

```bash
aws rds describe-db-instances \
  --db-instance-identifier bibliografia-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text
```

---

## Paso 3: Crear Lambda Function

### 3.1 Crear IAM Role para Lambda

```bash
# Crear role
aws iam create-role \
  --role-name lambda-bibliografia-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Agregar políticas básicas
aws iam attach-role-policy \
  --role-name lambda-bibliografia-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Agregar política para VPC (si RDS está en VPC)
aws iam attach-role-policy \
  --role-name lambda-bibliografia-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
```

### 3.2 Construir y subir Lambda Function

```bash
# 1. Construir package
./build_lambda.sh  # o build_lambda.ps1 en Windows

# 2. Crear función Lambda
aws lambda create-function \
  --function-name bibliografia-app \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-bibliografia-role \
  --handler lambda_handler.handler \
  --zip-file fileb://lambda_function.zip \
  --timeout 900 \
  --memory-size 1024 \
  --environment Variables="{
    DATABASE_URL=postgresql://admin:password@rds-endpoint:5432/bibliografia_db,
    CROSSREF_EMAIL=tu-email@example.com
  }" \
  --vpc-config "{
    SubnetIds=[subnet-xxx,subnet-yyy],
    SecurityGroupIds=[sg-xxx]
  }"
```

**Nota**: Si RDS es público, puedes omitir `--vpc-config`.

### 3.3 Actualizar función (cuando cambies código)

```bash
# Reconstruir
./build_lambda.sh

# Actualizar
aws lambda update-function-code \
  --function-name bibliografia-app \
  --zip-file fileb://lambda_function.zip
```

---

## Paso 4: Configurar API Gateway

### 4.1 Crear API Gateway REST API

```bash
# Crear API
aws apigatewayv2 create-api \
  --name bibliografia-api \
  --protocol-type HTTP \
  --cors-configuration AllowOrigins="*",AllowMethods="GET,POST,PUT,DELETE,OPTIONS",AllowHeaders="*"

# Obtener API ID
API_ID=$(aws apigatewayv2 get-apis --query "Items[?Name=='bibliografia-api'].ApiId" --output text)

# Crear integración con Lambda
aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:lambda:REGION:ACCOUNT_ID:function:bibliografia-app

# Crear ruta (catch-all)
aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key "$default" \
  --target "integrations/$INTEGRATION_ID"

# Crear stage
aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name prod \
  --auto-deploy
```

### 4.2 Obtener URL de la API

```bash
aws apigatewayv2 get-apis \
  --query "Items[?Name=='bibliografia-api'].ApiEndpoint" \
  --output text
```

---

## Paso 5: Desplegar Frontend en S3 + CloudFront

### 5.1 Crear bucket S3

```bash
aws s3 mb s3://bibliografia-frontend
aws s3 sync frontend/ s3://bibliografia-frontend/ --exclude "*.md"
```

### 5.2 Configurar CloudFront (opcional, para HTTPS)

```bash
aws cloudfront create-distribution \
  --origin-domain-name bibliografia-frontend.s3.amazonaws.com \
  --default-root-object index.html
```

---

## Paso 6: Inicializar Base de Datos

Después del primer despliegue, necesitas inicializar las tablas. Puedes hacerlo de dos formas:

### Opción A: Lambda de inicialización (una vez)

```python
# init_db_lambda.py
from app.database import init_db

def handler(event, context):
    init_db()
    return {"statusCode": 200, "body": "Database initialized"}
```

### Opción B: Desde tu máquina local (temporalmente)

```bash
# Conectar a RDS y ejecutar
psql -h rds-endpoint -U admin -d bibliografia_db
# Luego ejecutar: python -c "from app.database import init_db; init_db()"
```

---

## Paso 7: Configurar Variables de Entorno

Actualizar variables de entorno en Lambda:

```bash
aws lambda update-function-configuration \
  --function-name bibliografia-app \
  --environment Variables="{
    DATABASE_URL=postgresql://admin:password@rds-endpoint:5432/bibliografia_db,
    CROSSREF_EMAIL=tu-email@example.com,
    ALLOWED_ORIGINS=https://tu-dominio.com
  }"
```

---

## Costos Estimados (Uso Esporádico)

### Escenario: 20 requests/mes

| Servicio | Costo |
|----------|-------|
| **Lambda** (20 invocaciones, ~10s cada una) | ~$0.01 |
| **API Gateway** (20 requests) | ~$0.01 |
| **RDS db.t3.micro** | $15/mes |
| **S3** (frontend, ~10MB) | ~$0.01 |
| **CloudFront** (opcional) | ~$0.10 |
| **TOTAL** | **~$15.13/mes** |

**Comparación:**
- EC2 + RDS: $47/mes
- Lambda + RDS: $15/mes
- **Ahorro: $32/mes** 💰

---

## Consideraciones Importantes

### ⚠️ Límites de Lambda

1. **Tiempo máximo**: 15 minutos (suficiente para PDFs)
2. **Memoria**: Hasta 10GB (recomendado 1024MB para PDFs)
3. **Package size**: Máximo 250MB (descomprimido)
4. **Cold starts**: Primera invocación puede tardar 1-3 segundos

### 🔧 Optimizaciones

1. **Lambda Layers**: Para dependencias pesadas (pdfplumber)
2. **Provisioned Concurrency**: Para eliminar cold starts (costo adicional)
3. **Connection Pooling**: Para RDS desde Lambda

### 📝 Mejores Prácticas

1. **Manejo de errores**: Lambda debe retornar siempre una respuesta
2. **Logging**: Usa CloudWatch Logs
3. **Monitoreo**: Configura alertas en CloudWatch
4. **Backups**: RDS tiene backups automáticos

---

## Alternativa Más Fácil: AWS SAM

Si prefieres una herramienta que simplifique todo esto, usa **AWS SAM**:

```bash
# Instalar SAM CLI
pip install aws-sam-cli

# Inicializar proyecto
sam init

# Construir y desplegar
sam build
sam deploy --guided
```

SAM crea automáticamente:
- Lambda function
- API Gateway
- IAM roles
- Variables de entorno

---

## Troubleshooting

### Error: "Unable to import module"
- Verifica que todas las dependencias estén en el ZIP
- Usa `pip install -t .` para instalar en el directorio actual

### Error: "Timeout"
- Aumenta `--timeout` (máximo 900 segundos)
- Optimiza el procesamiento de PDFs

### Error: "Cannot connect to RDS"
- Verifica Security Groups
- Si RDS está en VPC, Lambda también debe estar en VPC
- Verifica que RDS sea públicamente accesible o esté en la misma VPC

### Cold Start lento
- Usa Lambda Layers para dependencias
- Considera Provisioned Concurrency (costo adicional)

---

## Próximos Pasos

1. ✅ Construir y probar Lambda localmente
2. ✅ Crear RDS instance
3. ✅ Desplegar Lambda function
4. ✅ Configurar API Gateway
5. ✅ Probar endpoints
6. ✅ Desplegar frontend en S3
7. ✅ Configurar dominio personalizado (opcional)

¿Necesitas ayuda con algún paso específico?

