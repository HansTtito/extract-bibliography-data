from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Document
from app.schemas import PDFUploadResponse, DocumentResponse
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
                    extracted_data['doi'] = doi  # Asegurar que el DOI esté presente
                    
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
                    # Si CrossRef no encuentra, hacer extracción manual
                    extracted_data = pdf_extractor.extract(pdf_content)
                    extracted_data['doi'] = doi
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

