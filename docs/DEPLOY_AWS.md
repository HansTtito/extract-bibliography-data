# Guía de Despliegue Completo en AWS

Esta guía te ayudará a desplegar toda la aplicación en AWS, incluyendo:
- FastAPI en Lambda
- GROBID en ECS Fargate o EC2
- RDS PostgreSQL
- S3 para PDFs y Frontend
- API Gateway
- CloudFront

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    CloudFront                            │
│              (Frontend estático)                         │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                           │
│              (REST API)                                  │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Lambda     │  │     RDS      │  │    GROBID    │
│  (FastAPI)   │  │  PostgreSQL  │  │ (ECS/EC2)    │
└──────┬───────┘  └──────────────┘  └──────────────┘
       │
       ▼
┌──────────────┐
│      S3     │
│   (PDFs)    │
└──────────────┘
```

## Requisitos Previos

1. **Cuenta de AWS** con permisos para crear recursos
2. **AWS CLI instalado y configurado**
   ```bash
   aws configure
   ```
3. **Terraform instalado** (>= 1.0)
   ```bash
   # Windows (Chocolatey)
   choco install terraform
   
   # Mac/Linux
   brew install terraform
   ```
4. **Python 3.11+** y dependencias instaladas
5. **Docker** (para construir Lambda package)

## Paso 1: Preparar el Código

### 1.1 Construir Package de Lambda

```bash
# Windows
.\infrastructure\build_lambda.ps1

# Linux/Mac
./infrastructure/build_lambda.sh
```

Esto crea `lambda_function.zip` con todo el código y dependencias.

### 1.2 Verificar Variables

Edita `infrastructure/terraform/variables.tf` o usa `terraform.tfvars`:

```hcl
environment        = "sandbox"
grobid_deployment  = "ec2"  # o "fargate"
aws_region        = "us-east-1"
crossref_email    = "tu-email@example.com"
```

## Paso 2: Desplegar con Terraform

### Opción A: Script Automatizado (Recomendado)

**Windows:**
```powershell
.\infrastructure\scripts\deploy_aws.ps1 -Environment sandbox -GrobidType ec2
```

**Linux/Mac:**
```bash
./infrastructure/scripts/deploy_aws.sh sandbox ec2
```

### Opción B: Manual con Terraform

```bash
cd infrastructure/terraform

# Inicializar
terraform init

# Plan (ver qué se va a crear)
terraform plan \
  -var="environment=sandbox" \
  -var="grobid_deployment=ec2"

# Aplicar (crear recursos)
terraform apply \
  -var="environment=sandbox" \
  -var="grobid_deployment=ec2" \
  -auto-approve
```

## Paso 3: Configurar Frontend

Después del despliegue, sube el frontend a S3:

```bash
# Obtener nombre del bucket
FRONTEND_BUCKET=$(terraform -chdir=infrastructure/terraform output -raw frontend_bucket)

# Subir frontend
aws s3 sync frontend/ s3://$FRONTEND_BUCKET --delete
```

## Paso 4: Verificar Despliegue

### Obtener URLs

```bash
cd infrastructure/terraform

# API Gateway
terraform output api_gateway_url

# Frontend
terraform output frontend_url

# GROBID
terraform output grobid_url
```

### Probar Endpoints

```bash
# Health check
curl $(terraform output -raw api_gateway_url)/health

# Probar GROBID
curl http://$(terraform output -raw grobid_url)/api/isalive
```

## Configuración de GROBID

### Opción 1: EC2 (Más Barato)

**Costo:** ~$2-3/mes

- Se crea automáticamente con Terraform
- Instancia t3.small spot
- GROBID se instala automáticamente

### Opción 2: ECS Fargate (Más Estable)

**Costo:** ~$15-25/mes

- Se crea automáticamente con Terraform
- ALB interno para balanceo
- Más estable y escalable

Cambiar en variables:
```hcl
grobid_deployment = "fargate"
```

## Variables de Entorno en Lambda

Terraform configura automáticamente:

- `DATABASE_URL`: Conexión a RDS
- `GROBID_URL`: URL de GROBID
- `USE_GROBID`: true
- `S3_BUCKET`: Bucket para PDFs
- `CROSSREF_EMAIL`: Tu email

## Costos Estimados

### Sandbox (EC2 + GROBID EC2)

| Servicio | Costo Mensual |
|----------|---------------|
| Lambda (100 invocaciones) | ~$0.10 |
| API Gateway | ~$0.10 |
| RDS db.t3.micro | $15 |
| S3 (10GB) | ~$0.25 |
| CloudFront | ~$0.10 |
| GROBID EC2 Spot | ~$2-3 |
| **TOTAL** | **~$17-18/mes** |

### Producción (Fargate + GROBID Fargate)

| Servicio | Costo Mensual |
|----------|---------------|
| Lambda (1000 invocaciones) | ~$1 |
| API Gateway | ~$1 |
| RDS db.t3.micro | $15 |
| S3 (50GB) | ~$1.25 |
| CloudFront | ~$1 |
| GROBID ECS Fargate | ~$15-25 |
| **TOTAL** | **~$34-44/mes** |

## Monitoreo

### CloudWatch Logs

```bash
# Logs de Lambda
aws logs tail /aws/lambda/bibliografia-sandbox --follow

# Logs de GROBID (ECS)
aws logs tail /ecs/grobid-service-sandbox --follow
```

### Métricas

- Lambda: Invocaciones, errores, duración
- RDS: CPU, memoria, conexiones
- GROBID: Health checks, tiempo de respuesta

## Actualizar Código

### 1. Reconstruir Lambda Package

```bash
.\infrastructure\build_lambda.ps1
```

### 2. Actualizar Lambda Function

```bash
aws lambda update-function-code \
  --function-name bibliografia-sandbox \
  --zip-file fileb://lambda_function.zip
```

O usar Terraform (detecta cambios automáticamente):

```bash
terraform apply
```

## Destruir Recursos

⚠️ **CUIDADO**: Esto elimina TODOS los recursos, incluyendo la base de datos.

```bash
cd infrastructure/terraform
terraform destroy
```

## Troubleshooting

### Error: "Lambda timeout"

- Aumentar `timeout` en `lambda.tf` (máximo 900s)
- Verificar que GROBID esté respondiendo

### Error: "Cannot connect to RDS"

- Verificar Security Groups
- Verificar que Lambda esté en VPC correcta
- Verificar que RDS esté en subnets privadas

### Error: "GROBID not available"

- Verificar que GROBID esté corriendo
- Verificar Security Groups
- Verificar URL en variables de entorno

### Error: "Package too large"

- Usar Lambda Layers para dependencias pesadas
- Optimizar dependencias

## Próximos Pasos

1. **Configurar dominio personalizado** (opcional)
2. **Configurar CI/CD** con GitHub Actions
3. **Configurar alertas** en CloudWatch
4. **Backups automáticos** de RDS
5. **Configurar WAF** para seguridad

## Referencias

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [GROBID Setup](GROBID_SETUP.md)

