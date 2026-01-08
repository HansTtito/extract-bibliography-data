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
    crossref_data = None
    
    # MEJORADO: Intentar enriquecer con CrossRef
    # Prioridad 1: Buscar por DOI (más preciso)
    if parsed_data.get('doi'):
        print(f"🔍 Buscando en CrossRef por DOI: {parsed_data['doi']}")
        crossref_data = crossref_service.search_by_doi(parsed_data['doi'])
        if crossref_data:
            print(f"✅ Encontrado en CrossRef por DOI")
    
    # Prioridad 2: Buscar por título y autores (si no hay DOI o no se encontró)
    if not crossref_data and original_title and len(original_title) > 10:
        print(f"🔍 Buscando en CrossRef por título: {original_title[:60]}...")
        crossref_data = crossref_service.search_by_title_author(
            title=original_title,
            authors=original_authors
        )
        if crossref_data:
            print(f"✅ Encontrado en CrossRef por título/autores")
    
    # Si encontramos datos en CrossRef, enriquecer
    if crossref_data:
        # Campos que siempre tomamos de CrossRef (más confiables)
        priority_fields = [
            'doi', 'link', 'isbn_issn', 'lugar_publicacion_entrega', 
            'publicista_editorial', 'volumen_edicion', 'numero_articulo_capitulo_informe',
            'paginas', 'tipo_documento', 'peer_reviewed', 'acceso_abierto'
        ]
        
        for field in priority_fields:
            if crossref_data.get(field):
                parsed_data[field] = crossref_data[field]
        
        # Título: usar CrossRef si el parseado es malo o incompleto
        if crossref_data.get('titulo_original'):
            if (not original_title or len(original_title) < 20 or 
                original_title.count(',') > 3):
                parsed_data['titulo_original'] = crossref_data['titulo_original']
            elif len(crossref_data['titulo_original']) > len(original_title or ''):
                parsed_data['titulo_original'] = crossref_data['titulo_original']
        
        # Autores: usar CrossRef si el parseado es incompleto
        if crossref_data.get('autores'):
            if not original_authors or len(original_authors) < 10:
                parsed_data['autores'] = crossref_data['autores']
            elif len(crossref_data['autores']) > len(original_authors or ''):
                parsed_data['autores'] = crossref_data['autores']
        
        # Año: preferir CrossRef si hay discrepancia
        if crossref_data.get('ano'):
            if not parsed_data.get('ano') or abs(crossref_data['ano'] - (parsed_data.get('ano') or 0)) <= 1:
                parsed_data['ano'] = crossref_data['ano']
        
        # Abstract y Keywords: solo de CrossRef (parser no los extrae de texto)
        if crossref_data.get('resumen_abstract'):
            parsed_data['resumen_abstract'] = crossref_data['resumen_abstract']
        if crossref_data.get('keywords'):
            parsed_data['keywords'] = crossref_data['keywords']
        
        enriched = True
        print(f"✅ Referencia enriquecida con CrossRef")
    else:
        print(f"⚠️  No se encontró en CrossRef, usando datos del parser")
    
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

