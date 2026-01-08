#!/usr/bin/env python3
"""
Script para limpiar la base de datos remotamente invocando una función Lambda
y también eliminar archivos PDF de S3 directamente
"""
import boto3
import json
import sys
from botocore.exceptions import ClientError

def clear_database_via_lambda():
    """Limpia la base de datos invocando el endpoint de API Gateway"""
    
    print("=" * 70)
    print("⚠️  ADVERTENCIA: Este script borrará:")
    print("   - TODOS los documentos de la base de datos")
    print("   - TODOS los jobs de procesamiento de la base de datos")
    print("   - TODOS los archivos PDF en S3 (carpeta uploads/)")
    print("=" * 70)
    
    # Confirmar
    try:
        confirm = input("\n¿Estás seguro? Escribe 'SI' para confirmar: ")
        if confirm != "SI":
            print("❌ Operación cancelada")
            return
    except (EOFError, KeyboardInterrupt):
        print("\n❌ Operación cancelada")
        return
    
    print("\n🚀 Iniciando limpieza...\n")
    
    # Primero, borrar archivos de S3 directamente
    print("📁 Eliminando archivos PDF de S3...")
    try:
        s3_client = boto3.client('s3', region_name='us-east-1')
        
        # Obtener nombre del bucket desde Terraform
        import subprocess
        import os
        
        terraform_dir = os.path.join(os.path.dirname(__file__), "infrastructure", "terraform")
        
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            check=True
        )
        
        outputs = json.loads(result.stdout)
        bucket_name = outputs["pdfs_bucket"]["value"]
        
        print(f"   Bucket: {bucket_name}")
        
        # Listar y eliminar archivos en uploads/
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix='uploads/')
        
        s3_files_before = 0
        s3_files_deleted = 0
        
        for page in pages:
            if 'Contents' in page:
                s3_files_before += len(page['Contents'])
                for obj in page['Contents']:
                    try:
                        s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
                        s3_files_deleted += 1
                    except ClientError as e:
                        print(f"   ⚠️  Error eliminando {obj['Key']}: {e}")
        
        if s3_files_before > 0:
            print(f"   ✅ Archivos S3 eliminados: {s3_files_deleted} de {s3_files_before}")
        else:
            print(f"   ℹ️  No había archivos en S3")
            
    except Exception as e:
        print(f"   ⚠️  Error eliminando archivos de S3: {e}")
        print("   Continuando con limpieza de BD...")
    
    print("")
    
    # Obtener la URL de API Gateway desde Terraform
    try:
        import subprocess
        import os
        
        terraform_dir = os.path.join(os.path.dirname(__file__), "infrastructure", "terraform")
        
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            check=True
        )
        
        outputs = json.loads(result.stdout)
        api_url = outputs["api_gateway_url"]["value"]
        
        print(f"🔗 API Gateway URL: {api_url}")
        
    except Exception as e:
        print(f"❌ Error obteniendo API URL de Terraform: {e}")
        return
    
    # Llamar al endpoint de limpieza
    try:
        import requests
        
        endpoint = f"{api_url}/api/admin/clear-database"
        print(f"📡 Llamando a: {endpoint}")
        
        response = requests.delete(endpoint, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Base de datos limpiada exitosamente!")
            print(f"📊 Documentos eliminados: {data.get('deleted', 0)}")
            print(f"📊 BD Documentos - Antes: {data.get('count_before', 0)} | Después: {data.get('count_after', 0)}")
            if 'jobs_deleted' in data:
                print(f"📊 BD Jobs - Eliminados: {data.get('jobs_deleted', 0)} (Antes: {data.get('jobs_before', 0)}, Después: {data.get('jobs_after', 0)})")
            if 's3_files_deleted' in data:
                print(f"📁 S3 - Archivos eliminados (vía endpoint): {data.get('s3_files_deleted', 0)} de {data.get('s3_files_before', 0)}")
            else:
                print("   (Los archivos de S3 ya fueron eliminados directamente)")
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"Respuesta: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error llamando al endpoint: {e}")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Verificar que requests esté instalado
    try:
        import requests
    except ImportError:
        print("❌ El módulo 'requests' no está instalado")
        print("💡 Instálalo con: pip install requests")
        sys.exit(1)
    
    clear_database_via_lambda()


