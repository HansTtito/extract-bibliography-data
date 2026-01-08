from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Document
from app.schemas import DocumentResponse

router = APIRouter(prefix="/api", tags=["Documents"])


@router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(
    skip: int = 0,
    limit: int = 1000,  # Aumentado de 100 a 1000 para mostrar más documentos
    db: Session = Depends(get_db)
):
    """Obtiene lista de documentos extraídos"""
    documents = db.query(Document).offset(skip).limit(limit).all()
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Obtiene un documento específico por ID"""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return DocumentResponse.model_validate(document)

