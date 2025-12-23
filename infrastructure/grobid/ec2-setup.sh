#!/bin/bash
# Script para configurar GROBID en EC2

set -e

echo "🚀 Configurando GROBID en EC2..."

# Instalar Docker
echo "📦 Instalando Docker..."
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# Instalar Docker Compose (opcional, pero útil)
echo "📦 Instalando Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Correr GROBID
echo "🐳 Iniciando GROBID..."
sudo docker run -d \
  --name grobid \
  -p 8070:8070 \
  --restart unless-stopped \
  -e JAVA_OPTS="-Xmx2g" \
  lfoppiano/grobid:0.7.3

# Esperar a que GROBID esté listo
echo "⏳ Esperando a que GROBID esté listo..."
sleep 30

# Verificar que está corriendo
if curl -f http://localhost:8070/api/isalive; then
    echo "✅ GROBID está corriendo correctamente"
else
    echo "❌ Error: GROBID no responde"
    exit 1
fi

# Configurar firewall (si es necesario)
echo "🔥 Configurando firewall..."
sudo firewall-cmd --permanent --add-port=8070/tcp || true
sudo firewall-cmd --reload || true

# Obtener IP pública
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
echo ""
echo "✅ GROBID configurado exitosamente!"
echo "📍 URL de GROBID: http://${PUBLIC_IP}:8070"
echo "🔗 Endpoint de salud: http://${PUBLIC_IP}:8070/api/isalive"
echo ""
echo "⚠️  IMPORTANTE: Configura el Security Group de EC2 para permitir tráfico en el puerto 8070"

