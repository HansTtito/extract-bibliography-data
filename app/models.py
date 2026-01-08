from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    numero_doc = Column(Integer, unique=True, index=True)  # N° doc
    
    # Información básica
    autores = Column(Text)  # Autor(es)
    ano = Column(Integer)  # Año
    titulo_original = Column(Text)  # Título original
    keywords = Column(Text)  # Keywords
    resumen_abstract = Column(Text)  # Resumen/Abstract
    
    # Información de publicación
    lugar_publicacion_entrega = Column(Text)  # Lugar de publicación/entrega
    publicista_editorial = Column(Text)  # Publicista/editorial
    volumen_edicion = Column(String(100))  # Volumen/edición
    isbn_issn = Column(String(50))  # ISBN/ISSN
    numero_articulo_capitulo_informe = Column(String(100))  # N° artículo/capítulo/informe
    paginas = Column(String(50))  # Páginas
    
    # Identificadores
    doi = Column(String(255))  # DOI
    link = Column(Text)  # Link
    
    # Clasificación
    idioma = Column(String(50))  # Idioma
    tipo_documento = Column(String(100))  # Tipo documento
    tipo_documento_otro = Column(String(100))  # Tipo documento (Otro)
    
    # Características
    peer_reviewed = Column(String(10))  # Peer-reviewed: "Sí" o "No"
    acceso_abierto = Column(String(10))  # Acceso abierto: "Sí" o "No"
    full_text_asociado_base_datos = Column(String(10))  # Full-text asociado a base de datos: "Sí" o "No"


class Job(Base):
    __tablename__ = "jobs"
    
    job_id = Column(String, primary_key=True)
    file_key = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    job_type = Column(String, default="pdf")  # "pdf" o "references"
    status = Column(String, default="pending")  # pending, processing, completed, failed
    progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    document_id = Column(Integer, ForeignKey("documents.numero_doc"), nullable=True)
    result = Column(JSONB, nullable=True)  # Para resultados complejos (múltiples documentos)

