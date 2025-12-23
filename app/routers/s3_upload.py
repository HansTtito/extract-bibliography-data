from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.config import settings
from app.models import Document
import boto3
from botocore.exceptions import ClientError
import uuid

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

