from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import MultipleReferencesResponse, DocumentResponse
from app.services.references_pdf_extractor import ReferencesPDFExtractor
from app.services.reference_parser import ReferenceParser
from app.services.crossref_service import CrossRefService
from app.middleware.rate_limiter import validate_pdf_size
from app.models import Document
import re


router = APIRouter(prefix="/api", tags=["References PDF"])

references_extractor = ReferencesPDFExtractor()
reference_parser = ReferenceParser()
crossref_service = CrossRefService()


def _process_single_reference(ref_text: str, db: Session) -> tuple:
    """Función auxiliar para procesar una sola referencia"""
    parsed_data = reference_parser.parse(ref_text.strip())
    
    original_title = parsed_data.get('titulo_original')
    original_authors = parsed_data.get('autores')
    enriched = False
    
    # Intentar enriquecer con CrossRef
    if parsed_data.get('doi'):
        crossref_data = crossref_service.search_by_doi(parsed_data['doi'])
        if crossref_data:
            priority_fields = ['lugar_publicacion_entrega', 'publicista_editorial', 
                             'volumen_edicion', 'isbn_issn', 'link', 'peer_reviewed', 
                             'acceso_abierto', 'resumen_abstract', 'keywords']
            
            for field in priority_fields:
                if crossref_data.get(field):
                    parsed_data[field] = crossref_data[field]
            
            if crossref_data.get('titulo_original'):
                if (not original_title or len(original_title) < 20 or 
                    original_title.count(',') > 3):
                    parsed_data['titulo_original'] = crossref_data['titulo_original']
                elif len(crossref_data['titulo_original']) > len(original_title or ''):
                    parsed_data['titulo_original'] = crossref_data['titulo_original']
            
            if crossref_data.get('autores'):
                if not original_authors or len(original_authors) < 10:
                    parsed_data['autores'] = crossref_data['autores']
                elif len(crossref_data['autores']) > len(original_authors or ''):
                    parsed_data['autores'] = crossref_data['autores']
            
            if crossref_data.get('ano'):
                parsed_data['ano'] = crossref_data['ano']
            
            enriched = True
    
    # Obtener siguiente número de documento
    last_doc = db.query(Document).order_by(Document.numero_doc.desc()).first()
    next_num = (last_doc.numero_doc + 1) if last_doc else 1
    
    # Crear documento
    document = Document(numero_doc=next_num, **parsed_data)
    db.add(document)
    db.commit()
    db.refresh(document)
    
    saved_document = db.query(Document).filter(Document.id == document.id).first()
    return DocumentResponse.model_validate(saved_document), enriched


@router.post("/upload-references-pdf", response_model=MultipleReferencesResponse)
async def upload_references_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Endpoint para subir un PDF con referencias bibliográficas y extraerlas todas"""
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")
    
    # Validar tamaño del archivo
    validate_pdf_size(file)
    
    try:
        # Leer contenido del PDF
        pdf_content = await file.read()
        
        # Extraer todas las referencias del PDF
        print(f"Procesando PDF: {file.filename}")
        references = references_extractor.extract_references(pdf_content)
        
        if not references:
            # Intentar extraer texto completo para debug
            import pdfplumber
            from io import BytesIO
            try:
                with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                    total_text = ""
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            total_text += page_text + "\n"
                    
                    # Buscar cualquier indicio de referencias
                    has_references_keyword = bool(re.search(r'references?|bibliography|literature\s+cited', total_text, re.IGNORECASE))
                    has_year_pattern = bool(re.search(r'\b(19\d{2}|20[0-2]\d)\b', total_text))
                    
                    error_detail = "No se pudieron extraer referencias del PDF. "
                    if not has_references_keyword:
                        error_detail += "No se encontró una sección 'References' o 'Bibliography' explícita. "
                    if not has_year_pattern:
                        error_detail += "No se encontraron años (formato 19XX o 20XX) en el documento. "
                    error_detail += "Verifica que el PDF contenga una sección de referencias bibliográficas."
                    
                    print(f"Debug - Tiene keyword de referencias: {has_references_keyword}")
                    print(f"Debug - Tiene patrones de año: {has_year_pattern}")
                    print(f"Debug - Longitud del texto: {len(total_text)}")
                    
            except Exception as debug_error:
                print(f"Error en debug: {debug_error}")
                error_detail = "No se pudieron extraer referencias del PDF. Verifica que el PDF contenga una sección de referencias."
            
            raise HTTPException(status_code=400, detail=error_detail)
        
        # Procesar cada referencia
        processed_docs = []
        failed_count = 0
        
        for ref_text in references:
            try:
                document, enriched = _process_single_reference(ref_text, db)
                processed_docs.append(document)
            except Exception as e:
                failed_count += 1
                print(f"Error procesando referencia: {e}")
                continue
        
        return MultipleReferencesResponse(
            success=True,
            message=f"Extraídas y procesadas {len(processed_docs)} de {len(references)} referencias del PDF",
            total=len(references),
            processed=len(processed_docs),
            failed=failed_count,
            documents=processed_docs
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando PDF de referencias: {str(e)}")

