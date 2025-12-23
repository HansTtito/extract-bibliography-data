#!/bin/bash
# Script para desplegar GROBID en AWS

set -e

ENVIRONMENT=${1:-sandbox}
DEPLOYMENT_TYPE=${2:-ec2}

echo "🚀 Desplegando GROBID para ambiente: ${ENVIRONMENT}"
echo "📦 Tipo de despliegue: ${DEPLOYMENT_TYPE}"

if [ "$DEPLOYMENT_TYPE" == "ec2" ]; then
    echo "🖥️  Desplegando en EC2 Spot..."
    
    # Crear EC2 spot instance
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id ami-0c55b159cbfafe1f0 \
        --instance-type t3.small \
        --spot-price "0.01" \
        --instance-market-options '{"MarketType":"spot","SpotOptions":{"SpotInstanceType":"one-time"}}' \
        --user-data file://infrastructure/grobid/ec2-setup.sh \
        --query 'Instances[0].InstanceId' \
        --output text)
    
    echo "⏳ Esperando a que la instancia esté lista..."
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID
    
    # Obtener IP pública
    PUBLIC_IP=$(aws ec2 describe-instances \
        --instance-ids $INSTANCE_ID \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text)
    
    echo "✅ Instancia EC2 creada: ${INSTANCE_ID}"
    echo "📍 IP Pública: ${PUBLIC_IP}"
    echo "🔗 URL de GROBID: http://${PUBLIC_IP}:8070"
    
    GROBID_URL="http://${PUBLIC_IP}:8070"
    
elif [ "$DEPLOYMENT_TYPE" == "fargate" ]; then
    echo "☁️  Desplegando en ECS Fargate..."
    
    # Registrar task definition
    aws ecs register-task-definition \
        --cli-input-json file://infrastructure/grobid/ecs-task-definition.json
    
    # Crear servicio (requiere VPC, subnets, security groups configurados)
    echo "⚠️  Nota: Necesitas configurar VPC, subnets y security groups antes de crear el servicio"
    echo "📝 Usa Terraform o AWS Console para crear el servicio ECS"
    
    GROBID_URL="http://grobid-alb-internal-123456789.us-east-1.elb.amazonaws.com:8070"
    
else
    echo "❌ Tipo de despliegue inválido: ${DEPLOYMENT_TYPE}"
    echo "Opciones: ec2, fargate"
    exit 1
fi

# Actualizar Lambda con URL de GROBID
if [ -n "$GROBID_URL" ]; then
    echo "🔧 Actualizando Lambda con URL de GROBID..."
    
    aws lambda update-function-configuration \
        --function-name bibliografia-${ENVIRONMENT} \
        --environment "Variables={GROBID_URL=${GROBID_URL},USE_GROBID=true}" \
        || echo "⚠️  No se pudo actualizar Lambda (puede que no exista aún)"
fi

echo ""
echo "✅ Despliegue completado!"
echo "📍 GROBID_URL=${GROBID_URL}"
echo ""
echo "🧪 Probar GROBID:"
echo "   curl http://${GROBID_URL#http://}/api/isalive"

