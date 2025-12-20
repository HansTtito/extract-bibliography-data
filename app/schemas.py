from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class DocumentBase(BaseModel):
    autores: Optional[str] = None
    ano: Optional[int] = None
    titulo_original: Optional[str] = None
    keywords: Optional[str] = None
    resumen_abstract: Optional[str] = None
    lugar_publicacion_entrega: Optional[str] = None
    publicista_editorial: Optional[str] = None
    volumen_edicion: Optional[str] = None
    isbn_issn: Optional[str] = None
    numero_articulo_capitulo_informe: Optional[str] = None
    paginas: Optional[str] = None
    doi: Optional[str] = None
    link: Optional[str] = None
    idioma: Optional[str] = None
    tipo_documento: Optional[str] = None
    tipo_documento_otro: Optional[str] = None
    peer_reviewed: Optional[str] = None
    acceso_abierto: Optional[str] = None
    full_text_asociado_base_datos: Optional[str] = None


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    id: int
    numero_doc: int

    class Config:
        from_attributes = True


class ReferenceInput(BaseModel):
    reference_text: str = Field(..., description="Texto de la referencia bibliográfica (puede contener múltiples referencias separadas por líneas)")


class MultipleReferencesInput(BaseModel):
    references: List[str] = Field(..., description="Lista de referencias bibliográficas a procesar")


class MultipleReferencesResponse(BaseModel):
    success: bool
    message: str
    total: int
    processed: int
    failed: int
    documents: List[DocumentResponse]


class PDFUploadResponse(BaseModel):
    success: bool
    message: str
    document: Optional[DocumentResponse] = None


class ReferenceUploadResponse(BaseModel):
    success: bool
    message: str
    document: Optional[DocumentResponse] = None
    enriched: bool = False

