from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.config import settings
from app.models import Document
from app.services.job_service import job_service, JobStatus
from app.schemas import JobResponse, DocumentResponse, ReferencesJobResponse
import boto3
from botocore.exceptions import ClientError
import uuid
import asyncio
import logging
import os
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["S3 Upload"])

# Cliente S3
s3_client = boto3.client('s3', region_name='us-east-1')


class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str = "application/pdf"


class PresignedUrlResponse(BaseModel):
    upload_url: str
    file_key: str
    expires_in: int = 3600


@router.post("/get-upload-url", response_model=PresignedUrlResponse)
async def get_presigned_upload_url(
    request: PresignedUrlRequest,
    db: Session = Depends(get_db)
):
    """
    Genera una URL presignada para que el frontend suba archivos directamente a S3.
    Esto evita el límite de 10 MB de API Gateway y mejora el rendimiento.
    """
    
    # Validar que sea PDF
    if not request.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")
    
    # Generar key único para S3
    file_extension = request.filename.split('.')[-1]
    unique_key = f"uploads/{uuid.uuid4()}.{file_extension}"
    
    try:
        # Generar URL presignada (válida por 1 hora)
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.s3_bucket,
                'Key': unique_key,
                'ContentType': request.content_type
            },
            ExpiresIn=3600,  # 1 hora
            HttpMethod='PUT'
        )
        
        return PresignedUrlResponse(
            upload_url=presigned_url,
            file_key=unique_key,
            expires_in=3600
        )
        
    except ClientError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando URL de upload: {str(e)}"
        )


class ProcessS3FileRequest(BaseModel):
    file_key: str


class ProcessS3FileAsyncRequest(BaseModel):
    file_key: str
    filename: str


@router.post("/process-s3-references-pdf-async")
async def process_s3_references_pdf_async(
    request: ProcessS3FileAsyncRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Inicia el procesamiento asíncrono de un PDF con referencias bibliográficas.
    Retorna un job_id inmediatamente para que el frontend pueda hacer polling.
    """
    from app.schemas import ReferencesJobResponse
    
    job_id = job_service.create_job(request.file_key, request.filename, job_type="references")
    
    # Iniciar la tarea de procesamiento en segundo plano
    background_tasks.add_task(process_references_pdf_background, job_id, request.file_key, db)
    
    job = job_service.get_job(job_id)
    return ReferencesJobResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        created_at=job["created_at"]
    )


async def process_references_pdf_background(job_id: str, file_key: str, db: Session):
    """
    Función que realiza el procesamiento real de las referencias del PDF en segundo plano.
    Actualiza el estado del job a través del JobService.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    from app.services.references_pdf_extractor import ReferencesPDFExtractor
    from app.services.reference_parser import ReferenceParser
    from app.services.crossref_service import CrossRefService
    from app.schemas import MultipleReferencesResponse, DocumentResponse
    from app.database import SessionLocal
    
    logger.info(f"Iniciando procesamiento de referencias en background para job_id: {job_id}, file_key: {file_key}")
    job_service.update_job_status(job_id, JobStatus.PROCESSING, progress=10)
    
    # Crear nueva sesión de BD para el background task
    db = SessionLocal()
    try:
        references_extractor = ReferencesPDFExtractor()
        reference_parser = ReferenceParser()
        crossref_service = CrossRefService()
        
        # Descargar PDF desde S3
        job_service.update_progress(job_id, 20)
        response = s3_client.get_object(
            Bucket=settings.s3_bucket,
            Key=file_key
        )
        pdf_content = response['Body'].read()
        
        # Extraer referencias usando GROBID (si está disponible) o regex
        job_service.update_progress(job_id, 30)
        references = references_extractor.extract_references(pdf_content)
        
        if not references:
            error_msg = "No se pudieron extraer referencias del PDF. Verifica que el PDF contenga una sección de referencias."
            logger.warning(f"Job {job_id}: {error_msg}")
            job_service.update_job_status(job_id, JobStatus.FAILED, error=error_msg)
            return
        
        total_refs = len(references)
        logger.info(f"Job {job_id}: Extraídas {total_refs} referencias del PDF")
        
        # Procesar cada referencia
        processed_docs = []
        failed_count = 0
        
        for idx, ref_text in enumerate(references, 1):
            try:
                # Actualizar progreso (30% + 60% * (idx / total_refs))
                progress = 30 + int(60 * (idx / total_refs))
                job_service.update_progress(job_id, progress)
                
                logger.debug(f"[REF {idx}/{total_refs}] Texto extraído: {ref_text[:200]}...")
                
                # Parse reference
                parsed_ref = reference_parser.parse(ref_text)
                logger.debug(f"[REF {idx}/{total_refs}] Parsed data: {parsed_ref}")
                
                # Validar que al menos tenga título o autores
                if not parsed_ref.get('titulo_original') and not parsed_ref.get('autores'):
                    logger.debug(f"[REF {idx}/{total_refs}] SKIP: No tiene título ni autores")
                    failed_count += 1
                    continue
                
                # Try to enrich with CrossRef if we have DOI
                if parsed_ref.get('doi'):
                    try:
                        crossref_data = crossref_service.search_by_doi(parsed_ref['doi'])
                        if crossref_data:
                            parsed_ref.update(crossref_data)
                            logger.debug(f"[REF {idx}/{total_refs}] Enriquecida con CrossRef")
                    except Exception as ce:
                        logger.debug(f"[REF {idx}/{total_refs}] CrossRef error: {ce}")
                        pass
                
                # Get next numero_doc
                last_doc = db.query(Document).order_by(Document.numero_doc.desc()).first()
                next_numero = (last_doc.numero_doc + 1) if last_doc else 1
                
                # Create document
                document = Document(
                    numero_doc=next_numero,
                    autores=parsed_ref.get('autores'),
                    ano=parsed_ref.get('ano'),
                    titulo_original=parsed_ref.get('titulo_original'),
                    lugar_publicacion_entrega=parsed_ref.get('lugar_publicacion_entrega'),
                    publicista_editorial=parsed_ref.get('editorial'),
                    volumen_edicion=parsed_ref.get('volumen_edicion'),
                    paginas=parsed_ref.get('paginas'),
                    doi=parsed_ref.get('doi'),
                    isbn_issn=parsed_ref.get('isbn_issn')
                )
                
                db.add(document)
                db.commit()
                db.refresh(document)
                
                logger.info(f"[REF {idx}/{total_refs}] ✓ Guardada: {document.titulo_original or document.autores}")
                processed_docs.append(DocumentResponse.model_validate(document))
                
            except Exception as e:
                import traceback
                failed_count += 1
                logger.error(f"[REF {idx}/{total_refs}] ERROR: {e}")
                logger.debug(f"[REF {idx}/{total_refs}] Traceback: {traceback.format_exc()}")
                db.rollback()  # Rollback en caso de error
                continue
        
        # Crear respuesta
        result = MultipleReferencesResponse(
            success=True,
            message=f"Extraídas y procesadas {len(processed_docs)} de {total_refs} referencias del PDF",
            total=total_refs,
            processed=len(processed_docs),
            failed=failed_count,
            documents=processed_docs
        )
        
        job_service.update_job_status(job_id, JobStatus.COMPLETED, result=result)
        logger.info(f"Procesamiento de referencias completado para job_id: {job_id}")
        
    except ClientError as e:
        error_msg = f"Archivo no encontrado en S3: {str(e)}"
        logger.error(f"Job {job_id} failed: {error_msg}")
        job_service.update_job_status(job_id, JobStatus.FAILED, error=error_msg)
    except Exception as e:
        error_msg = f"Error procesando PDF de referencias: {str(e)}"
        logger.error(f"Job {job_id} failed: {error_msg}")
        job_service.update_job_status(job_id, JobStatus.FAILED, error=error_msg)
    finally:
        db.close()


@router.post("/process-s3-references-pdf")
async def process_s3_references_pdf(
    request: ProcessS3FileRequest,
    db: Session = Depends(get_db)
):
    """
    Procesa un PDF con referencias bibliográficas que ya fue subido a S3.
    Extrae todas las referencias del PDF y las guarda en la BD.
    """
    from app.services.references_pdf_extractor import ReferencesPDFExtractor
    from app.services.reference_parser import ReferenceParser
    from app.services.crossref_service import CrossRefService
    from app.schemas import MultipleReferencesResponse, DocumentResponse
    
    references_extractor = ReferencesPDFExtractor()
    reference_parser = ReferenceParser()
    crossref_service = CrossRefService()
    
    try:
        # Descargar PDF desde S3
        response = s3_client.get_object(
            Bucket=settings.s3_bucket,
            Key=request.file_key
        )
        pdf_content = response['Body'].read()
        
        # Extraer referencias usando GROBID (si está disponible) o regex
        references = references_extractor.extract_references(pdf_content)
        
        if not references:
            raise HTTPException(
                status_code=400,
                detail="No se pudieron extraer referencias del PDF. Verifica que el PDF contenga una sección de referencias."
            )
        
        # Procesar cada referencia
        processed_docs = []
        failed_count = 0
        
        for idx, ref_text in enumerate(references, 1):
            try:
                print(f"[REF {idx}] Texto extraído: {ref_text[:200]}...")
                
                # Parse reference
                parsed_ref = reference_parser.parse(ref_text)
                print(f"[REF {idx}] Parsed data: {parsed_ref}")
                
                # Validar que al menos tenga título o autores
                if not parsed_ref.get('titulo_original') and not parsed_ref.get('autores'):
                    print(f"[REF {idx}] SKIP: No tiene título ni autores")
                    failed_count += 1
                    continue
                
                # Try to enrich with CrossRef if we have DOI
                if parsed_ref.get('doi'):
                    try:
                        crossref_data = crossref_service.search_by_doi(parsed_ref['doi'])
                        if crossref_data:
                            parsed_ref.update(crossref_data)
                            print(f"[REF {idx}] Enriquecida con CrossRef")
                    except Exception as ce:
                        print(f"[REF {idx}] CrossRef error: {ce}")
                        pass
                
                # Get next numero_doc
                last_doc = db.query(Document).order_by(Document.numero_doc.desc()).first()
                next_numero = (last_doc.numero_doc + 1) if last_doc else 1
                
                # Create document
                document = Document(
                    numero_doc=next_numero,
                    autores=parsed_ref.get('autores'),
                    ano=parsed_ref.get('ano'),
                    titulo_original=parsed_ref.get('titulo_original'),
                    lugar_publicacion_entrega=parsed_ref.get('lugar_publicacion_entrega'),
                    publicista_editorial=parsed_ref.get('editorial'),
                    volumen_edicion=parsed_ref.get('volumen_edicion'),
                    paginas=parsed_ref.get('paginas'),
                    doi=parsed_ref.get('doi'),
                    isbn_issn=parsed_ref.get('isbn_issn')
                )
                
                db.add(document)
                db.commit()
                db.refresh(document)
                
                print(f"[REF {idx}] ✓ Guardada: {document.titulo_original or document.autores}")
                processed_docs.append(DocumentResponse.model_validate(document))
                
            except Exception as e:
                import traceback
                failed_count += 1
                print(f"[REF {idx}] ERROR: {e}")
                print(f"[REF {idx}] Traceback: {traceback.format_exc()}")
                db.rollback()  # Rollback en caso de error
                continue
        
        return MultipleReferencesResponse(
            success=True,
            message=f"Extraídas y procesadas {len(processed_docs)} de {len(references)} referencias del PDF",
            total=len(references),
            processed=len(processed_docs),
            failed=failed_count,
            documents=processed_docs
        )
        
    except ClientError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Archivo no encontrado en S3: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando PDF de referencias: {str(e)}"
        )


@router.post("/process-s3-pdf")
async def process_s3_pdf(
    request: ProcessS3FileRequest,
    db: Session = Depends(get_db)
):
    """
    Procesa un PDF que ya fue subido a S3.
    Este endpoint se llama DESPUÉS de que el frontend suba el archivo a S3.
    """
    from app.services.pdf_extractor import PDFExtractor
    from app.services.crossref_service import CrossRefService
    from app.models import Document
    from app.utils.text_processing import extract_doi
    from io import BytesIO
    import pdfplumber
    
    pdf_extractor = PDFExtractor()
    crossref_service = CrossRefService()
    
    try:
        # Descargar PDF desde S3
        response = s3_client.get_object(
            Bucket=settings.s3_bucket,
            Key=request.file_key
        )
        pdf_content = response['Body'].read()
        
        # Extraer DOI primero
        doi = None
        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                if pdf.pages:
                    first_page_text = pdf.pages[0].extract_text() or ""
                    doi = extract_doi(first_page_text)
        except:
            pass
        
        extracted_data = {}
        
        # Si hay DOI, usar CrossRef PRIMERO
        if doi:
            try:
                crossref_data = crossref_service.search_by_doi(doi)
                if crossref_data:
                    extracted_data = crossref_data.copy()
                    extracted_data['doi'] = doi
                    
                    # Complementar con PDF si falta información
                    if not extracted_data.get('resumen_abstract'):
                        pdf_data = pdf_extractor.extract(pdf_content)
                        if pdf_data.get('resumen_abstract'):
                            extracted_data['resumen_abstract'] = pdf_data['resumen_abstract']
                    
                    if not extracted_data.get('keywords'):
                        pdf_data = pdf_extractor.extract(pdf_content)
                        if pdf_data.get('keywords'):
                            extracted_data['keywords'] = pdf_data['keywords']
                else:
                    extracted_data = pdf_extractor.extract(pdf_content)
                    extracted_data['doi'] = doi
            except Exception as e:
                print(f"Error usando CrossRef: {e}")
                extracted_data = pdf_extractor.extract(pdf_content)
                extracted_data['doi'] = doi
        else:
            # Sin DOI: usar solo extracción del PDF (con GROBID si está disponible)
            extracted_data = pdf_extractor.extract(pdf_content)
        
        # Obtener último numero_doc
        last_doc = db.query(Document).order_by(Document.numero_doc.desc()).first()
        next_numero = (last_doc.numero_doc + 1) if last_doc else 1
        
        # Crear documento en BD
        document = Document(
            numero_doc=next_numero,
            autores=extracted_data.get('autores'),
            ano=extracted_data.get('ano'),
            titulo_original=extracted_data.get('titulo_original'),
            keywords=extracted_data.get('keywords'),
            resumen_abstract=extracted_data.get('resumen_abstract'),
            lugar_publicacion_entrega=extracted_data.get('lugar_publicacion_entrega'),
            publicista_editorial=extracted_data.get('editorial'),
            volumen_edicion=extracted_data.get('volumen_edicion'),
            isbn_issn=extracted_data.get('isbn_issn'),
            numero_articulo_capitulo_informe=extracted_data.get('numero_articulo_capitulo_informe'),
            paginas=extracted_data.get('paginas'),
            doi=extracted_data.get('doi'),
            link=extracted_data.get('link'),
            idioma=extracted_data.get('idioma'),
            tipo_documento=extracted_data.get('tipo_documento'),
            tipo_documento_otro=extracted_data.get('tipo_documento_otro'),
            peer_reviewed=extracted_data.get('peer_reviewed'),
            acceso_abierto=extracted_data.get('acceso_abierto'),
            full_text_asociado_base_datos=extracted_data.get('full_text_asociado_base_datos')
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Opcionalmente: eliminar archivo de S3 después de procesar
        # s3_client.delete_object(Bucket=settings.s3_bucket, Key=request.file_key)
        
        from app.schemas import DocumentResponse
        return {
            "message": "PDF procesado exitosamente desde S3",
            "document": DocumentResponse.model_validate(document)
        }
        
    except ClientError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Archivo no encontrado en S3: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando PDF: {str(e)}"
        )


def process_pdf_background(job_id: str, file_key: str, db: Session):
    """Función que procesa el PDF en background"""
    from app.services.pdf_extractor import PDFExtractor
    from app.services.crossref_service import CrossRefService
    from app.utils.text_processing import extract_doi
    from io import BytesIO
    import pdfplumber
    
    try:
        # Actualizar estado a procesando
        job_service.update_job_status(job_id, JobStatus.PROCESSING, progress=10)
        
        # Descargar PDF desde S3
        response = s3_client.get_object(
            Bucket=settings.s3_bucket,
            Key=file_key
        )
        pdf_content = response['Body'].read()
        
        job_service.update_progress(job_id, 20)
        
        # Extraer DOI primero
        doi = None
        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                if pdf.pages:
                    first_page_text = pdf.pages[0].extract_text() or ""
                    doi = extract_doi(first_page_text)
        except:
            pass
        
        job_service.update_progress(job_id, 30)
        
        pdf_extractor = PDFExtractor()
        crossref_service = CrossRefService()
        extracted_data = {}
        
        # Si hay DOI, usar CrossRef PRIMERO
        if doi:
            try:
                crossref_data = crossref_service.search_by_doi(doi)
                if crossref_data:
                    extracted_data = crossref_data.copy()
                    extracted_data['doi'] = doi
                    
                    # Complementar con PDF si falta información
                    if not extracted_data.get('resumen_abstract'):
                        pdf_data = pdf_extractor.extract(pdf_content)
                        if pdf_data.get('resumen_abstract'):
                            extracted_data['resumen_abstract'] = pdf_data['resumen_abstract']
                    
                    if not extracted_data.get('keywords'):
                        pdf_data = pdf_extractor.extract(pdf_content)
                        if pdf_data.get('keywords'):
                            extracted_data['keywords'] = pdf_data['keywords']
                else:
                    extracted_data = pdf_extractor.extract(pdf_content)
                    extracted_data['doi'] = doi
            except Exception as e:
                print(f"Error usando CrossRef: {e}")
                extracted_data = pdf_extractor.extract(pdf_content)
                extracted_data['doi'] = doi
        else:
            # Sin DOI: usar solo extracción del PDF
            extracted_data = pdf_extractor.extract(pdf_content)
        
        job_service.update_progress(job_id, 70)
        
        # Obtener último numero_doc
        last_doc = db.query(Document).order_by(Document.numero_doc.desc()).first()
        next_numero = (last_doc.numero_doc + 1) if last_doc else 1
        
        job_service.update_progress(job_id, 80)
        
        # Crear documento en BD
        document = Document(
            numero_doc=next_numero,
            autores=extracted_data.get('autores'),
            ano=extracted_data.get('ano'),
            titulo_original=extracted_data.get('titulo_original'),
            keywords=extracted_data.get('keywords'),
            resumen_abstract=extracted_data.get('resumen_abstract'),
            lugar_publicacion_entrega=extracted_data.get('lugar_publicacion_entrega'),
            publicista_editorial=extracted_data.get('editorial'),
            volumen_edicion=extracted_data.get('volumen_edicion'),
            isbn_issn=extracted_data.get('isbn_issn'),
            numero_articulo_capitulo_informe=extracted_data.get('numero_articulo_capitulo_informe'),
            paginas=extracted_data.get('paginas'),
            doi=extracted_data.get('doi'),
            link=extracted_data.get('link'),
            idioma=extracted_data.get('idioma'),
            tipo_documento=extracted_data.get('tipo_documento'),
            tipo_documento_otro=extracted_data.get('tipo_documento_otro'),
            peer_reviewed=extracted_data.get('peer_reviewed'),
            acceso_abierto=extracted_data.get('acceso_abierto'),
            full_text_asociado_base_datos=extracted_data.get('full_text_asociado_base_datos')
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        job_service.update_progress(job_id, 95)
        
        # Actualizar job como completado
        job_service.update_job_status(
            job_id, 
            JobStatus.COMPLETED, 
            document=DocumentResponse.model_validate(document)
        )
        
    except ClientError as e:
        job_service.update_job_status(
            job_id, 
            JobStatus.FAILED, 
            error=f"Archivo no encontrado en S3: {str(e)}"
        )
    except Exception as e:
        import traceback
        error_msg = f"Error procesando PDF: {str(e)}"
        print(f"Error en background job {job_id}: {error_msg}")
        print(traceback.format_exc())
        job_service.update_job_status(
            job_id, 
            JobStatus.FAILED, 
            error=error_msg
        )


@router.post("/process-s3-pdf-async", response_model=JobResponse)
async def process_s3_pdf_async(
    request: ProcessS3FileAsyncRequest
):
    """
    Inicia el procesamiento asíncrono de un PDF que ya fue subido a S3.
    Retorna inmediatamente con un job_id para consultar el estado.
    
    El procesamiento real se hace en una Lambda Worker separada que consume
    mensajes de SQS, permitiendo que este endpoint responda en < 1 segundo.
    """
    import json
    import os
    
    # Crear job (sin depender de DB para respuesta rápida - job_service es en memoria)
    job_id = job_service.create_job(request.file_key, request.filename)
    
    # Enviar mensaje a SQS para procesamiento asíncrono
    try:
        queue_url = os.getenv('PDF_PROCESSING_QUEUE_URL')
        if not queue_url:
            raise ValueError("PDF_PROCESSING_QUEUE_URL no configurada")
        
        sqs_client = boto3.client('sqs', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({
                'job_id': job_id,
                'file_key': request.file_key,
                'filename': request.filename
            })
        )
        
        logger.info(f"Job {job_id} enviado a SQS para procesamiento")
        
    except Exception as e:
        logger.error(f"Error enviando mensaje a SQS: {e}")
        # Si falla SQS, marcar job como fallido
        job_service.update_job_status(
            job_id,
            JobStatus.FAILED,
            error=f"Error enviando a cola de procesamiento: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error iniciando procesamiento: {str(e)}"
        )
    
    # Retornar job inmediatamente (sin esperar procesamiento)
    job = job_service.get_job(job_id)
    return JobResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job["progress"],
        message="Procesamiento iniciado",
        created_at=job["created_at"]
    )


@router.post("/internal/process-pdf")
async def internal_process_pdf(request: dict):
    """
    Endpoint interno para procesar PDFs (invocado asíncronamente).
    No expuesto públicamente, solo para invocación interna de Lambda.
    """
    from app.database import SessionLocal
    
    job_id = request.get('job_id')
    file_key = request.get('file_key')
    
    if not job_id or not file_key:
        raise HTTPException(status_code=400, detail="job_id y file_key requeridos")
    
    db = SessionLocal()
    try:
        process_pdf_background(job_id, file_key, db)
    finally:
        db.close()
    
    return {"status": "processed"}


@router.get("/job-status/{job_id}")
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Consulta el estado de un job de procesamiento (PDF individual o referencias).
    """
    job = job_service.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    
    job_type = job.get("job_type", "pdf")
    
    # Determinar mensaje según estado
    if job["status"] == JobStatus.PENDING:
        message = "Esperando procesamiento..."
    elif job["status"] == JobStatus.PROCESSING:
        message = f"Procesando... {job['progress']}%"
    elif job["status"] == JobStatus.ANALYZING:
        message = f"Analizando contenido del PDF... {job['progress']}%"
    elif job["status"] == JobStatus.COMPLETED:
        message = "Procesamiento completado"
    elif job["status"] == JobStatus.FAILED:
        message = f"Error: {job.get('error', 'Error desconocido')}"
    else:
        message = f"Estado desconocido: {job['status']}"
    
    if job_type == "references":
        # Retornar ReferencesJobResponse para jobs de referencias
        return ReferencesJobResponse(
            job_id=job["job_id"],
            status=job["status"],
            progress=job["progress"],
            message=message,
            result=job.get("result"),
            error=job.get("error"),
            created_at=job["created_at"],
            started_at=job.get("started_at"),
            completed_at=job.get("completed_at")
        )
    else:
        # Retornar JobResponse para jobs de PDF individual
        return JobResponse(
            job_id=job["job_id"],
            status=job["status"],
            progress=job["progress"],
            message=message,
            document=DocumentResponse.model_validate(job["document"]) if job.get("document") else None,
            error=job.get("error"),
            created_at=job["created_at"],
            started_at=job.get("started_at"),
            completed_at=job.get("completed_at")
        )

