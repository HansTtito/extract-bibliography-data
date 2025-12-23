#!/bin/bash
# Script para desplegar la aplicación completa en AWS

set -e

ENVIRONMENT=${1:-sandbox}
GROBID_TYPE=${2:-ec2}
AWS_REGION=${3:-us-east-1}

echo "🚀 Desplegando aplicación en AWS"
echo "   Ambiente: ${ENVIRONMENT}"
echo "   GROBID: ${GROBID_TYPE}"
echo "   Región: ${AWS_REGION}"
echo ""

# Verificar requisitos
echo "📋 Verificando requisitos..."
command -v aws >/dev/null 2>&1 || { echo "❌ AWS CLI no está instalado"; exit 1; }
command -v terraform >/dev/null 2>&1 || { echo "❌ Terraform no está instalado"; exit 1; }
command -v zip >/dev/null 2>&1 || { echo "❌ zip no está instalado"; exit 1; }

# Verificar credenciales de AWS
echo "🔐 Verificando credenciales de AWS..."
aws sts get-caller-identity >/dev/null 2>&1 || { echo "❌ AWS credentials no configuradas"; exit 1; }
echo "✅ Credenciales OK"
echo ""

# Construir package de Lambda
echo "📦 Construyendo package de Lambda..."
cd "$(dirname "$0")/../.."
./infrastructure/build_lambda.sh || {
    echo "⚠️  Error construyendo Lambda package, intentando método alternativo..."
    mkdir -p lambda_package
    cd lambda_package
    pip install -r ../requirements.txt -t .
    cp -r ../app .
    cp ../lambda_handler.py .
    cd ..
    zip -r lambda_function.zip lambda_package/*
    rm -rf lambda_package
}
echo "✅ Package de Lambda creado"
echo ""

# Inicializar Terraform
echo "🏗️  Inicializando Terraform..."
cd infrastructure/terraform
terraform init
echo ""

# Aplicar configuración
echo "🚀 Aplicando configuración de Terraform..."
terraform apply \
  -var="environment=${ENVIRONMENT}" \
  -var="grobid_deployment=${GROBID_TYPE}" \
  -var="aws_region=${AWS_REGION}" \
  -auto-approve

echo ""
echo "✅ Despliegue completado!"
echo ""
echo "📋 URLs importantes:"
terraform output -json | jq -r '
  "API Gateway: " + .api_gateway_url.value,
  "Frontend: https://" + .frontend_url.value,
  "GROBID: " + .grobid_url.value
'

echo ""
echo "🔐 Credenciales de RDS (guardar de forma segura):"
terraform output -json | jq -r '.rds_password.value' | head -1

echo ""
echo "📝 Próximos pasos:"
echo "   1. Subir frontend a S3: aws s3 sync frontend/ s3://$(terraform output -raw frontend_bucket)"
echo "   2. Configurar CORS en API Gateway si es necesario"
echo "   3. Probar la API: curl $(terraform output -raw api_gateway_url)/health"

