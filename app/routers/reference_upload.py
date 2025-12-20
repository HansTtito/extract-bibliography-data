import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Document
from app.schemas import (
    ReferenceInput, ReferenceUploadResponse, DocumentResponse,
    MultipleReferencesInput, MultipleReferencesResponse
)
from app.services.reference_parser import ReferenceParser
from app.services.crossref_service import CrossRefService

router = APIRouter(prefix="/api", tags=["Reference"])

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


@router.post("/upload-reference", response_model=ReferenceUploadResponse)
async def upload_reference(
    reference: ReferenceInput,
    db: Session = Depends(get_db)
):
    """Endpoint para subir una referencia bibliográfica y extraer información.
    Si el texto contiene múltiples referencias (separadas por líneas), procesa solo la primera."""
    
    try:
        # Por ahora, procesar solo la primera referencia si hay múltiples líneas
        references_text = reference.reference_text.strip()
        lines = [line.strip() for line in references_text.split('\n') if line.strip()]
        
        # Usar la primera línea que parezca una referencia completa
        ref_text = references_text
        if len(lines) > 1:
            # Buscar la primera línea que tenga formato de referencia
            for line in lines:
                if re.search(r'\b(19|20)\d{2}\b', line) and len(line) > 30:
                    ref_text = line
                    break
        
        # Procesar la referencia
        document, enriched = _process_single_reference(ref_text, db)
        
        return ReferenceUploadResponse(
            success=True,
            message="Referencia procesada exitosamente",
            document=document,
            enriched=enriched
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando referencia: {str(e)}")


@router.post("/upload-multiple-references", response_model=MultipleReferencesResponse)
async def upload_multiple_references(
    references: MultipleReferencesInput,
    db: Session = Depends(get_db)
):
    """Endpoint para procesar múltiples referencias bibliográficas a la vez"""
    
    processed_docs = []
    failed_count = 0
    
    for ref_text in references.references:
        if not ref_text.strip():
            continue
            
        try:
            document, enriched = _process_single_reference(ref_text, db)
            processed_docs.append(document)
        except Exception as e:
            failed_count += 1
            print(f"Error procesando referencia: {e}")
            continue
    
    return MultipleReferencesResponse(
        success=True,
        message=f"Procesadas {len(processed_docs)} de {len(references.references)} referencias",
        total=len(references.references),
        processed=len(processed_docs),
        failed=failed_count,
        documents=processed_docs
    )

