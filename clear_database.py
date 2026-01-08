#!/usr/bin/env python3
"""
Script para limpiar completamente la base de datos Y el bucket S3
ADVERTENCIA: Esto borrará TODOS los documentos y PDFs
"""
import sys
import os
import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Document, Base
from app.config import settings

def clear_s3_bucket():
    """Limpia todos los archivos del bucket S3"""
    bucket_name = settings.s3_bucket
    print(f"\n📦 Limpiando bucket S3: {bucket_name}")
    
    try:
        s3 = boto3.client('s3')
        
        # Listar todos los objetos
        print("🔍 Listando objetos en S3...")
        response = s3.list_objects_v2(Bucket=bucket_name)
        
        if 'Contents' not in response:
            print("✅ El bucket S3 ya está vacío")
            return 0
        
        objects = response['Contents']
        total_objects = len(objects)
        print(f"📊 Encontrados {total_objects} archivos en S3")
        
        # Borrar todos los objetos
        if total_objects > 0:
            print("🗑️  Borrando archivos de S3...")
            objects_to_delete = [{'Key': obj['Key']} for obj in objects]
            s3.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': objects_to_delete}
            )
            print(f"✅ {total_objects} archivos eliminados de S3")
        
        return total_objects
        
    except Exception as e:
        print(f"❌ Error limpiando S3: {e}")
        import traceback
        traceback.print_exc()
        return 0

def clear_database(database_url: str):
    """Limpia todos los registros de la base de datos"""
    print("\n💾 Limpiando base de datos...")
    print(f"🔗 Conectando a: {database_url.split('@')[-1]}...")  # Solo mostrar el host
    
    # Crear conexión directa con la URL proporcionada
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Contar documentos antes
        count_before = db.query(Document).count()
        print(f"📊 Documentos actuales: {count_before}")
        
        if count_before == 0:
            print("✅ La base de datos ya está vacía")
            return 0
        
        # Borrar todos los documentos
        print("🗑️  Borrando documentos de la base de datos...")
        deleted = db.query(Document).delete()
        db.commit()
        
        print(f"✅ {deleted} documentos eliminados de la base de datos")
        
        # Verificar
        count_after = db.query(Document).count()
        print(f"📊 Documentos restantes: {count_after}")
        
        # Reiniciar secuencia (si existe)
        try:
            # Para PostgreSQL, reiniciar la secuencia del ID
            db.execute("ALTER SEQUENCE documents_id_seq RESTART WITH 1")
            db.commit()
            print("✅ Secuencia de IDs reiniciada")
        except Exception as e:
            print(f"⚠️  No se pudo reiniciar secuencia (puede ser normal): {e}")
        
        return deleted
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error limpiando base de datos: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        db.close()

def get_database_url():
    """Obtiene la URL de la base de datos de AWS"""
    # Intentar obtener de variable de entorno
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        print("✅ Usando DATABASE_URL de variable de entorno")
        return database_url
    
    # Si no existe, intentar obtener de Terraform
    print("🔍 Obteniendo DATABASE_URL de Terraform...")
    try:
        import subprocess
        
        terraform_dir = os.path.join(os.path.dirname(__file__), "infrastructure", "terraform")
        
        # Obtener outputs de Terraform
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            check=True
        )
        
        import json
        outputs = json.loads(result.stdout)
        
        # Construir DATABASE_URL desde los outputs
        if "rds_endpoint" in outputs:
            endpoint = outputs["rds_endpoint"]["value"]
            username = outputs.get("rds_username", {}).get("value", "postgres")
            password = outputs.get("rds_password", {}).get("value", "")
            database = outputs.get("rds_database", {}).get("value", "bibliografia")
            
            database_url = f"postgresql://{username}:{password}@{endpoint}/{database}"
            print("✅ DATABASE_URL obtenida de Terraform")
            return database_url
        else:
            print("❌ No se encontró 'rds_endpoint' en Terraform outputs")
            return None
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando Terraform: {e}")
        print(f"Salida: {e.stderr}")
        return None
    except Exception as e:
        print(f"❌ Error obteniendo DATABASE_URL: {e}")
        return None

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Limpia completamente la base de datos y el bucket S3')
    parser.add_argument('--confirm', action='store_true', help='Confirmar limpieza sin preguntar')
    args = parser.parse_args()
    
    print("=" * 70)
    print("⚠️  ADVERTENCIA: Este script borrará:")
    print("   - TODOS los documentos de la base de datos")
    print("   - TODOS los archivos PDF del bucket S3")
    print("=" * 70)
    
    # Obtener DATABASE_URL
    print("\n🔗 Configurando conexión a la base de datos...")
    database_url = get_database_url()
    
    if not database_url:
        print("\n❌ No se pudo obtener DATABASE_URL")
        print("💡 Puedes configurarla manualmente:")
        print("   export DATABASE_URL='postgresql://user:pass@host/db'")
        print("   O ejecutar desde el directorio con Terraform configurado")
        return
    
    # Confirmar
    if not args.confirm:
        try:
            confirm = input("\n¿Estás seguro? Escribe 'SI' para confirmar: ")
            if confirm != "SI":
                print("❌ Operación cancelada")
                return
        except (EOFError, KeyboardInterrupt):
            print("\n❌ Operación cancelada")
            return
    else:
        print("\n✅ Confirmación automática activada (--confirm)")
    
    print("\n🚀 Iniciando limpieza completa...\n")
    
    # 1. Limpiar S3
    s3_deleted = clear_s3_bucket()
    
    # 2. Limpiar base de datos
    db_deleted = clear_database(database_url)
    
    # Resumen
    print("\n" + "=" * 70)
    print("📊 RESUMEN DE LIMPIEZA:")
    print(f"   - Archivos eliminados de S3: {s3_deleted}")
    print(f"   - Documentos eliminados de BD: {db_deleted}")
    print("=" * 70)
    print("\n✅ Limpieza completa finalizada!")

if __name__ == "__main__":
    main()

