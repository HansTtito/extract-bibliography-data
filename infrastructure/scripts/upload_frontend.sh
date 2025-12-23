#!/bin/bash
# Script para subir el frontend a S3
# Uso: ./infrastructure/scripts/upload_frontend.sh

ENVIRONMENT=${1:-sandbox}
AWS_REGION=${2:-us-east-1}

echo "Subiendo frontend a S3..."

# Obtener nombre del bucket desde Terraform
cd infrastructure/terraform
BUCKET_NAME=$(terraform output -raw frontend_bucket)

if [ -z "$BUCKET_NAME" ]; then
    echo "❌ Error: No se pudo obtener el nombre del bucket"
    echo "Asegúrate de que Terraform esté desplegado"
    exit 1
fi

echo "Bucket: $BUCKET_NAME"
echo ""

# Volver al directorio raíz
cd ../..

# Verificar que existe la carpeta frontend
if [ ! -d "frontend" ]; then
    echo "❌ Error: No se encontró la carpeta frontend"
    exit 1
fi

# Subir archivos
echo "Subiendo archivos..."
aws s3 sync frontend/ "s3://$BUCKET_NAME" \
    --delete \
    --region $AWS_REGION \
    --exclude ".git/*" \
    --exclude "*.md"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Frontend subido exitosamente!"
    echo ""
    echo "URLs:"
    FRONTEND_URL=$(cd infrastructure/terraform && terraform output -raw frontend_url)
    echo "  Frontend: https://$FRONTEND_URL"
else
    echo ""
    echo "❌ Error al subir el frontend"
    exit 1
    fi

