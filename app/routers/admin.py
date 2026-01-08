"""
Router para operaciones administrativas
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Document, Job
from app.config import settings
from typing import Dict
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Cliente S3
s3_client = boto3.client('s3', region_name='us-east-1')


@router.delete("/clear-database")
async def clear_database(db: Session = Depends(get_db)) -> Dict:
    """
    🔴 ADVERTENCIA: Elimina TODOS los documentos, jobs de la base de datos Y todos los archivos PDF de S3
    Este endpoint debe ser protegido en producción
    """
    try:
        # Contar documentos y jobs antes
        count_before = db.query(Document).count()
        jobs_before = db.query(Job).count()
        logger.info(f"Documentos antes de limpiar: {count_before}")
        logger.info(f"Jobs antes de limpiar: {jobs_before}")
        
        # Contar archivos en S3 antes
        s3_files_before = 0
        s3_files_deleted = 0
        try:
            # Listar todos los objetos en el bucket (específicamente en uploads/)
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=settings.s3_bucket, Prefix='uploads/')
            
            for page in pages:
                if 'Contents' in page:
                    s3_files_before += len(page['Contents'])
                    # Eliminar cada archivo
                    for obj in page['Contents']:
                        try:
                            s3_client.delete_object(Bucket=settings.s3_bucket, Key=obj['Key'])
                            s3_files_deleted += 1
                            logger.debug(f"Archivo eliminado de S3: {obj['Key']}")
                        except ClientError as e:
                            logger.warning(f"Error eliminando {obj['Key']}: {e}")
            
            logger.info(f"Archivos en S3 antes: {s3_files_before}, eliminados: {s3_files_deleted}")
        except ClientError as e:
            logger.warning(f"Error accediendo a S3: {e}")
            s3_files_before = 0
            s3_files_deleted = 0
        
        if count_before == 0 and jobs_before == 0 and s3_files_before == 0:
            return {
                "message": "La base de datos y S3 ya están vacíos",
                "deleted": 0,
                "count_before": 0,
                "count_after": 0,
                "jobs_before": 0,
                "jobs_deleted": 0,
                "s3_files_before": 0,
                "s3_files_deleted": 0
            }
        
        # Borrar todos los jobs primero (por la foreign key)
        jobs_deleted = db.query(Job).delete()
        logger.info(f"Jobs eliminados: {jobs_deleted}")
        
        # Borrar todos los documentos
        deleted = db.query(Document).delete()
        db.commit()
        
        # Verificar
        count_after = db.query(Document).count()
        jobs_after = db.query(Job).count()
        
        # Reiniciar secuencia (si existe)
        try:
            db.execute("ALTER SEQUENCE documents_id_seq RESTART WITH 1")
            db.commit()
            logger.info("Secuencia de IDs reiniciada")
        except Exception as e:
            logger.warning(f"No se pudo reiniciar secuencia: {e}")
        
        logger.info(f"Base de datos limpiada: {deleted} documentos eliminados, {jobs_deleted} jobs eliminados")
        logger.info(f"S3 limpiado: {s3_files_deleted} archivos eliminados")
        
        return {
            "message": "Base de datos y S3 limpiados exitosamente",
            "deleted": deleted,
            "count_before": count_before,
            "count_after": count_after,
            "jobs_before": jobs_before,
            "jobs_deleted": jobs_deleted,
            "jobs_after": jobs_after,
            "s3_files_before": s3_files_before,
            "s3_files_deleted": s3_files_deleted
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error limpiando base de datos y S3: {e}")
        raise HTTPException(status_code=500, detail=f"Error limpiando base de datos y S3: {str(e)}")


