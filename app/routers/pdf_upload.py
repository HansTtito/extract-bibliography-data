from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Document
from app.schemas import PDFUploadResponse, DocumentResponse, MultiplePDFsResponse
from app.services.pdf_extractor import PDFExtractor
from app.services.crossref_service import CrossRefService

router = APIRouter(prefix="/api", tags=["PDF"])

pdf_extractor = PDFExtractor()
crossref_service = CrossRefService()


@router.post("/upload-pdf", response_model=PDFUploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Endpoint para subir un PDF y extraer información bibliográfica"""
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")
    
    try:
        # Leer contenido del PDF
        pdf_content = await file.read()
        
        # PRIMERO: Intentar extraer DOI para usar CrossRef (más confiable)
        # Extraer solo DOI primero sin procesar todo el PDF
        from app.utils.text_processing import extract_doi
        from io import BytesIO
        import pdfplumber
        
        doi = None
        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                first_page_text = pdf.pages[0].extract_text() or "" if pdf.pages else ""
                doi = extract_doi(first_page_text)
        except:
            pass
        
        extracted_data = {}
        
        # Si hay DOI, usar CrossRef PRIMERO (más confiable)
        if doi:
            try:
                crossref_data = crossref_service.search_by_doi(doi)
                if crossref_data:
                    # Usar datos de CrossRef como base (son más confiables)
                    extracted_data = crossref_data.copy()
                    # Usar el DOI completo de CrossRef si está disponible
                    if crossref_data.get('doi'):
                        extracted_data['doi'] = crossref_data['doi']
                    else:
                        extracted_data['doi'] = doi
                    
                    # Si CrossRef no tiene abstract o keywords, intentar extraer del PDF
                    if not extracted_data.get('resumen_abstract'):
                        pdf_data = pdf_extractor.extract(pdf_content)
                        if pdf_data.get('resumen_abstract'):
                            extracted_data['resumen_abstract'] = pdf_data['resumen_abstract']
                    
                    if not extracted_data.get('keywords'):
                        pdf_data = pdf_extractor.extract(pdf_content)
                        if pdf_data.get('keywords'):
                            extracted_data['keywords'] = pdf_data['keywords']
                else:
                    # Si CrossRef no encuentra con DOI parcial, intentar búsqueda por título
                    print(f"DOI {doi} no encontrado en CrossRef, intentando extracción manual...")
                    pdf_data = pdf_extractor.extract(pdf_content)
                    extracted_data = pdf_data
                    extracted_data['doi'] = doi
                    
                    # Si tenemos título, intentar buscar en CrossRef por título
                    if pdf_data.get('titulo_original'):
                        try:
                            crossref_by_title = crossref_service.search_by_title_author(
                                pdf_data['titulo_original']
                            )
                            if crossref_by_title and crossref_by_title.get('autores'):
                                # Usar autores de CrossRef si están disponibles
                                extracted_data['autores'] = crossref_by_title['autores']
                                # Actualizar DOI si CrossRef tiene uno completo
                                if crossref_by_title.get('doi'):
                                    extracted_data['doi'] = crossref_by_title['doi']
                        except:
                            pass
            except Exception as e:
                # Si falla CrossRef, hacer extracción manual
                print(f"Error al consultar CrossRef: {e}")
                extracted_data = pdf_extractor.extract(pdf_content)
                if doi:
                    extracted_data['doi'] = doi
        else:
            # Si no hay DOI, hacer extracción manual completa
            extracted_data = pdf_extractor.extract(pdf_content)
        
        # Obtener siguiente número de documento
        last_doc = db.query(Document).order_by(Document.numero_doc.desc()).first()
        next_num = (last_doc.numero_doc + 1) if last_doc else 1
        
        # Crear documento en base de datos
        document = Document(
            numero_doc=next_num,
            **extracted_data
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        return PDFUploadResponse(
            success=True,
            message="PDF procesado exitosamente",
            document=DocumentResponse.model_validate(document)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando PDF: {str(e)}")


@router.post("/upload-multiple-pdfs", response_model=MultiplePDFsResponse)
async def upload_multiple_pdfs(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Endpoint para subir múltiples PDFs y extraer información bibliográfica de cada uno"""
    
    if not files:
        raise HTTPException(status_code=400, detail="No se proporcionaron archivos")
    
    # Filtrar solo PDFs
    pdf_files = [f for f in files if f.filename and f.filename.endswith('.pdf')]
    
    if not pdf_files:
        raise HTTPException(status_code=400, detail="No se encontraron archivos PDF válidos")
    
    processed_docs = []
    failed_count = 0
    errors = []
    
    for i, file in enumerate(pdf_files, 1):
        try:
            # Leer contenido del PDF
            pdf_content = await file.read()
            
            # Extraer DOI primero
            from app.utils.text_processing import extract_doi
            from io import BytesIO
            import pdfplumber
            
            doi = None
            try:
                with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                    first_page_text = pdf.pages[0].extract_text() or "" if pdf.pages else ""
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
                        
                        # Complementar con PDF si falta abstract o keywords
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
                    print(f"Error al consultar CrossRef para {file.filename}: {e}")
                    extracted_data = pdf_extractor.extract(pdf_content)
                    if doi:
                        extracted_data['doi'] = doi
            else:
                extracted_data = pdf_extractor.extract(pdf_content)
            
            # Obtener siguiente número de documento
            last_doc = db.query(Document).order_by(Document.numero_doc.desc()).first()
            next_num = (last_doc.numero_doc + 1) if last_doc else 1
            
            # Crear documento en base de datos
            document = Document(
                numero_doc=next_num,
                **extracted_data
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
            processed_docs.append(DocumentResponse.model_validate(document))
            
        except Exception as e:
            failed_count += 1
            error_msg = f"Error procesando {file.filename}: {str(e)}"
            errors.append(error_msg)
            print(error_msg)
            continue
    
    return MultiplePDFsResponse(
        success=True,
        message=f"Procesados {len(processed_docs)} de {len(pdf_files)} PDFs",
        total=len(pdf_files),
        processed=len(processed_docs),
        failed=failed_count,
        documents=processed_docs,
        errors=errors if errors else None
    )

