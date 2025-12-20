#!/bin/bash
# Script para construir el package de Lambda
# Uso: ./build_lambda.sh

echo "Construyendo package para Lambda..."

# Limpiar build anterior si existe
rm -rf lambda_package lambda_function.zip

# Crear directorio temporal
mkdir -p lambda_package
cd lambda_package

echo "Instalando dependencias..."
# Instalar dependencias en el directorio actual
pip install -r ../requirements.txt -t . --quiet

echo "Copiando código de la aplicación..."
# Copiar código de la aplicación
cp -r ../app .
cp ../lambda_handler.py .

# Crear ZIP
echo "Creando archivo ZIP..."
cd ..
zip -r lambda_function.zip lambda_package/* -q

# Limpiar directorio temporal
rm -rf lambda_package

# Mostrar tamaño
ZIP_SIZE=$(du -h lambda_function.zip | cut -f1)
echo ""
echo "✅ Package creado: lambda_function.zip ($ZIP_SIZE)"
echo "⚠️  Nota: Lambda tiene un límite de 250MB descomprimido"

