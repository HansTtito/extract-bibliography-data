import pandas as pd
import json
from io import BytesIO
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models import Document


class ExportService:
    """Servicio para exportar datos en diferentes formatos"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_documents(self) -> List[Document]:
        """Obtiene todos los documentos de la base de datos"""
        return self.db.query(Document).order_by(Document.numero_doc).all()
    
    def export_to_csv(self) -> BytesIO:
        """Exporta documentos a CSV"""
        documents = self.get_all_documents()
        df = self._documents_to_dataframe(documents)
        
        output = BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)
        return output
    
    def export_to_excel(self) -> BytesIO:
        """Exporta documentos a Excel"""
        documents = self.get_all_documents()
        df = self._documents_to_dataframe(documents)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Documentos')
        output.seek(0)
        return output
    
    def export_to_json(self) -> str:
        """Exporta documentos a JSON"""
        documents = self.get_all_documents()
        data = [self._document_to_dict(doc) for doc in documents]
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def _documents_to_dataframe(self, documents: List[Document]) -> pd.DataFrame:
        """Convierte lista de documentos a DataFrame de pandas"""
        data = []
        for doc in documents:
            data.append(self._document_to_dict(doc))
        
        # Mapear nombres de columnas a español según especificación
        df = pd.DataFrame(data)
        
        # Renombrar columnas a los nombres en español
        column_mapping = {
            'numero_doc': 'N° doc',
            'autores': 'Autor(es)',
            'ano': 'Año',
            'titulo_original': 'Título original',
            'keywords': 'Keywords',
            'resumen_abstract': 'Resumen/Abstract',
            'lugar_publicacion_entrega': 'Lugar de publicación/entrega',
            'publicista_editorial': 'Publicista/editorial',
            'volumen_edicion': 'Volumen/edición',
            'isbn_issn': 'ISBN/ISSN',
            'numero_articulo_capitulo_informe': 'N° artículo/capítulo/informe',
            'paginas': 'Páginas',
            'doi': 'DOI',
            'link': 'Link',
            'idioma': 'Idioma',
            'tipo_documento': 'Tipo documento',
            'tipo_documento_otro': 'Tipo documento (Otro)',
            'peer_reviewed': 'Peer-reviewed',
            'acceso_abierto': 'Acceso abierto',
            'full_text_asociado_base_datos': 'Full-text asociado a base de datos'
        }
        
        df = df.rename(columns=column_mapping)
        
        # Reordenar columnas según especificación
        column_order = [
            'N° doc', 'Autor(es)', 'Año', 'Título original', 'Keywords',
            'Resumen/Abstract', 'Lugar de publicación/entrega', 'Publicista/editorial',
            'Volumen/edición', 'ISBN/ISSN', 'N° artículo/capítulo/informe', 'Páginas',
            'DOI', 'Link', 'Idioma', 'Tipo documento', 'Tipo documento (Otro)',
            'Peer-reviewed', 'Acceso abierto', 'Full-text asociado a base de datos'
        ]
        
        # Asegurar que todas las columnas existan
        for col in column_order:
            if col not in df.columns:
                df[col] = None
        
        return df[column_order]
    
    def _document_to_dict(self, doc: Document) -> Dict[str, Any]:
        """Convierte un documento a diccionario"""
        return {
            'numero_doc': doc.numero_doc,
            'autores': doc.autores,
            'ano': doc.ano,
            'titulo_original': doc.titulo_original,
            'keywords': doc.keywords,
            'resumen_abstract': doc.resumen_abstract,
            'lugar_publicacion_entrega': doc.lugar_publicacion_entrega,
            'publicista_editorial': doc.publicista_editorial,
            'volumen_edicion': doc.volumen_edicion,
            'isbn_issn': doc.isbn_issn,
            'numero_articulo_capitulo_informe': doc.numero_articulo_capitulo_informe,
            'paginas': doc.paginas,
            'doi': doc.doi,
            'link': doc.link,
            'idioma': doc.idioma,
            'tipo_documento': doc.tipo_documento,
            'tipo_documento_otro': doc.tipo_documento_otro,
            'peer_reviewed': doc.peer_reviewed,
            'acceso_abierto': doc.acceso_abierto,
            'full_text_asociado_base_datos': doc.full_text_asociado_base_datos
        }

