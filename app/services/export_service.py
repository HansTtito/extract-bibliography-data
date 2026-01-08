import pandas as pd
import json
import re
from io import BytesIO
from typing import List, Dict, Any, Optional
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
        try:
        documents = self.get_all_documents()
        df = self._documents_to_dataframe(documents)
        
        # Sanitizar datos antes de exportar a Excel
        df = self._sanitize_dataframe_for_excel(df)
            
            # Asegurar que los nombres de columnas sean válidos para Excel
            # Excel tiene límite de 255 caracteres para nombres de columnas
            df.columns = [str(col)[:255] if len(str(col)) > 255 else str(col) for col in df.columns]
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Usar un nombre de hoja válido (máximo 31 caracteres, sin caracteres especiales)
                sheet_name = 'Documentos'[:31]
                df.to_excel(writer, index=False, sheet_name=sheet_name)
        output.seek(0)
        return output
        except Exception as e:
            # Log del error para debugging
            import traceback
            print(f"Error al exportar a Excel: {e}")
            print(traceback.format_exc())
            raise
    
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
    
    def _sanitize_text_for_excel(self, value: Any) -> Optional[str]:
        """
        Sanitiza texto para Excel eliminando caracteres problemáticos
        
        Args:
            value: Valor a sanitizar (puede ser str, int, None, etc.)
            
        Returns:
            String sanitizado o None
        """
        if value is None:
            return None
        
        # Convertir a string si no lo es
        if not isinstance(value, str):
            value = str(value)
        
        # Excel tiene un límite de 32,767 caracteres por celda
        # Truncar si es muy largo (dejar un margen)
        MAX_EXCEL_CELL_LENGTH = 32000
        if len(value) > MAX_EXCEL_CELL_LENGTH:
            value = value[:MAX_EXCEL_CELL_LENGTH] + "... [truncado]"
        
        # Eliminar caracteres de control (excepto tab, newline, carriage return)
        # Caracteres de control: 0x00-0x1F excepto 0x09 (tab), 0x0A (LF), 0x0D (CR)
        value = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', value)
        
        # Eliminar caracteres no válidos para XML (que usa Excel)
        # Caracteres no válidos en XML 1.0: 0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F
        # También eliminar caracteres sustitutos UTF-16 (0xD800-0xDFFF)
        value = re.sub(r'[\uD800-\uDFFF]', '', value)
        
        # Normalizar saltos de línea: convertir \r\n y \r a \n
        value = re.sub(r'\r\n|\r', '\n', value)
        
        # Reemplazar múltiples saltos de línea consecutivos por uno solo
        value = re.sub(r'\n{3,}', '\n\n', value)
        
        # Eliminar espacios en blanco al inicio y final de cada línea
        lines = value.split('\n')
        value = '\n'.join(line.strip() for line in lines)
        
        # Eliminar espacios múltiples (más de 2 espacios seguidos)
        value = re.sub(r' {3,}', '  ', value)
        
        # Limpiar espacios al inicio y final del texto completo
        value = value.strip()
        
        # Retornar None si el string está vacío después de la limpieza
        return value if value else None
    
    def _sanitize_dataframe_for_excel(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sanitiza un DataFrame para exportación a Excel
        
        Args:
            df: DataFrame a sanitizar
            
        Returns:
            DataFrame sanitizado
        """
        df = df.copy()
        
        # Aplicar sanitización a todas las columnas de texto
        for col in df.columns:
            if df[col].dtype == 'object':  # Columnas de texto
                df[col] = df[col].apply(self._sanitize_text_for_excel)
        
        # Reemplazar NaN y None con strings vacíos para Excel
        df = df.fillna('')
        
        return df

