"""
Servicio para manejar jobs de procesamiento asíncrono usando Base de Datos
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, Optional
from enum import Enum
from app.database import SessionLocal
from app.models import Job, Document

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    ANALYZING = "analyzing"  # Estado específico para cuando se está analizando el PDF
    COMPLETED = "completed"
    FAILED = "failed"


class JobService:
    """Servicio para manejar jobs de procesamiento asíncrono usando Base de Datos"""
    
    def create_job(self, file_key: str, filename: str, job_type: str = "pdf") -> str:
        """Crea un nuevo job en BD y retorna su ID
        
        Args:
            file_key: Clave del archivo en S3
            filename: Nombre del archivo
            job_type: Tipo de job ("pdf" o "references")
        """
        db = SessionLocal()
        try:
            job_id = str(uuid.uuid4())
            job = Job(
                job_id=job_id,
                file_key=file_key,
                filename=filename,
                job_type=job_type,
                status=JobStatus.PENDING.value,
                progress=0
            )
            db.add(job)
            db.commit()
            logger.info(f"Job creado: {job_id} para archivo {filename} (tipo: {job_type})")
            return job_id
        except Exception as e:
            db.rollback()
            logger.error(f"Error creando job: {e}")
            raise
        finally:
            db.close()
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Obtiene el estado de un job desde BD"""
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if not job:
                return None
            
            result = {
                "job_id": job.job_id,
                "file_key": job.file_key,
                "filename": job.filename,
                "job_type": job.job_type,
                "status": job.status,
                "progress": job.progress,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error": job.error,
                "result": job.result
            }
            
            # Si hay document_id, cargar el documento
            if job.document_id:
                document = db.query(Document).filter(Document.numero_doc == job.document_id).first()
                if document:
                    from app.schemas import DocumentResponse
                    result["document"] = DocumentResponse.model_validate(document)
            
            return result
        except Exception as e:
            logger.error(f"Error obteniendo job {job_id}: {e}")
            return None
        finally:
            db.close()
    
    def update_job_status(self, job_id: str, status: JobStatus, **kwargs):
        """Actualiza el estado de un job en BD"""
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if not job:
                logger.warning(f"Job no encontrado: {job_id}")
                return
            
            job.status = status.value
            
            if status == JobStatus.PROCESSING:
                job.started_at = datetime.utcnow()
                job.progress = kwargs.get("progress", 10)
            elif status == JobStatus.ANALYZING:
                # Si no hay started_at, establecerlo
                if not job.started_at:
                    job.started_at = datetime.utcnow()
                job.progress = kwargs.get("progress", 40)
            elif status == JobStatus.COMPLETED:
                job.completed_at = datetime.utcnow()
                job.progress = 100
                if "document" in kwargs:
                    # Si se pasa un DocumentResponse (Pydantic model), extraer el numero_doc
                    document = kwargs["document"]
                    # DocumentResponse puede ser un Pydantic model o un dict
                    if hasattr(document, 'numero_doc'):
                        job.document_id = document.numero_doc
                    elif hasattr(document, 'model_dump'):
                        # Es un Pydantic model, convertir a dict
                        doc_dict = document.model_dump()
                        job.document_id = doc_dict.get('numero_doc')
                    elif isinstance(document, dict) and 'numero_doc' in document:
                        job.document_id = document['numero_doc']
                if "result" in kwargs:
                    job.result = kwargs["result"]
            elif status == JobStatus.FAILED:
                job.completed_at = datetime.utcnow()
                job.error = kwargs.get("error", "Error desconocido")
                job.progress = 0
            
            db.commit()
            logger.info(f"Job {job_id} actualizado a {status.value}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error actualizando job {job_id}: {e}")
            raise
        finally:
            db.close()
    
    def update_progress(self, job_id: str, progress: int):
        """Actualiza el progreso de un job en BD"""
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if job:
                job.progress = progress
                db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error actualizando progreso del job {job_id}: {e}")
        finally:
            db.close()


# Instancia global del servicio
job_service = JobService()
