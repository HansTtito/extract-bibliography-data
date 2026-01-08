"""
Handler para Lambda Worker que procesa PDFs desde SQS
"""
import json
import os
import logging
import boto3
from app.services.job_service import job_service, JobStatus
from app.services.pdf_extractor import PDFExtractor
from app.services.crossref_service import CrossRefService
from app.utils.text_processing import extract_doi
from app.database import SessionLocal, init_db
from app.models import Document
from app.schemas import DocumentResponse
from app.config import settings
from io import BytesIO
import pdfplumber
from botocore.exceptions import ClientError

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Inicializar base de datos
try:
    init_db()
    logger.info("✅ Base de datos inicializada correctamente")
except Exception as e:
    logger.error(f"⚠️ Error inicializando base de datos: {e}")

# Cliente S3
s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))


def process_pdf_from_sqs(job_id: str, file_key: str, filename: str):
    """Procesa un PDF desde S3 usando job_id y file_key"""
    db = SessionLocal()
    try:
        # Actualizar estado a procesando
        job_service.update_job_status(job_id, JobStatus.PROCESSING, progress=10)
        logger.info(f"Job {job_id} iniciado para archivo {filename}")
        
        # Descargar PDF desde S3
        response = s3_client.get_object(
            Bucket=settings.s3_bucket,
            Key=file_key
        )
        pdf_content = response['Body'].read()
        logger.info(f"PDF descargado de S3: {len(pdf_content)} bytes")
        
        job_service.update_progress(job_id, 20)
        
        # Extraer DOI primero
        doi = None
        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                if pdf.pages:
                    first_page_text = pdf.pages[0].extract_text() or ""
                    doi = extract_doi(first_page_text)
                    if doi:
                        logger.info(f"DOI encontrado: {doi}")
        except Exception as e:
            logger.warning(f"Error extrayendo DOI: {e}")
        
        job_service.update_progress(job_id, 30)
        
        # Cambiar a estado "analizando" cuando empieza la extracción
        job_service.update_job_status(job_id, JobStatus.ANALYZING, progress=40)
        logger.info(f"Job {job_id} analizando contenido del PDF...")
        
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
                    logger.info("Datos enriquecidos con CrossRef")
                    
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
                logger.warning(f"Error usando CrossRef: {e}")
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
        
        logger.info(f"Documento creado: #{document.numero_doc} - {document.titulo_original}")
        
        job_service.update_progress(job_id, 95)
        
        # Actualizar job como completado
        job_service.update_job_status(
            job_id, 
            JobStatus.COMPLETED, 
            document=DocumentResponse.model_validate(document)
        )
        
        logger.info(f"Job {job_id} completado exitosamente")
        
    except ClientError as e:
        error_msg = f"Archivo no encontrado en S3: {str(e)}"
        logger.error(f"Job {job_id} falló: {error_msg}")
        job_service.update_job_status(
            job_id, 
            JobStatus.FAILED, 
            error=error_msg
        )
        raise  # Re-raise para que SQS reintente
    except Exception as e:
        import traceback
        error_msg = f"Error procesando PDF: {str(e)}"
        logger.error(f"Job {job_id} falló: {error_msg}")
        logger.error(traceback.format_exc())
        job_service.update_job_status(
            job_id, 
            JobStatus.FAILED, 
            error=error_msg
        )
        raise  # Re-raise para que SQS reintente
    finally:
        db.close()


def handler(event, context):
    """
    Handler para Lambda Worker que procesa mensajes de SQS
    
    Event format (SQS):
    {
        "Records": [
            {
                "body": "{\"job_id\": \"...\", \"file_key\": \"...\", \"filename\": \"...\"}"
            }
        ]
    }
    """
    logger.info(f"Worker recibió evento con {len(event.get('Records', []))} mensajes")
    
    for record in event.get('Records', []):
        try:
            # Parsear mensaje de SQS
            message_body = json.loads(record['body'])
            job_id = message_body.get('job_id')
            file_key = message_body.get('file_key')
            filename = message_body.get('filename', 'unknown.pdf')
            
            if not job_id or not file_key:
                logger.error(f"Mensaje inválido: falta job_id o file_key")
                continue
            
            logger.info(f"Procesando job {job_id} para archivo {file_key}")
            
            # Procesar PDF
            process_pdf_from_sqs(job_id, file_key, filename)
            
        except Exception as e:
            logger.error(f"Error procesando mensaje: {str(e)}")
            # Re-raise para que SQS reintente el mensaje
            raise
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Procesamiento completado"})
    }
