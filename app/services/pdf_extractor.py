import re
import pdfplumber
from typing import Dict, Optional
from io import BytesIO
from app.utils.text_processing import extract_doi, extract_year, extract_isbn_issn, normalize_text


class PDFExtractor:
    """Servicio para extraer información bibliográfica de PDFs"""
    
    def extract(self, pdf_content: bytes) -> Dict[str, Optional[str]]:
        """Extrae información bibliográfica de un PDF"""
        doc = {}
        
        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                # Extraer texto de todas las páginas
                full_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
                
                if not full_text:
                    return doc
                
                # Extraer información usando patrones
                # DOI
                doi = extract_doi(full_text)
                if doi:
                    doc['doi'] = doi
                
                # Año
                year = extract_year(full_text)
                if year:
                    doc['ano'] = year
                
                # ISBN/ISSN
                isbn_issn = extract_isbn_issn(full_text)
                if isbn_issn:
                    doc['isbn_issn'] = isbn_issn
                
                # Intentar extraer título (generalmente en la primera página, en negrita o grande)
                title = self._extract_title(pdf, full_text)
                if title:
                    doc['titulo_original'] = normalize_text(title)
                
                # Intentar extraer autores (generalmente después del título o en metadata)
                authors = self._extract_authors(full_text)
                if authors:
                    doc['autores'] = authors
                
                # Intentar extraer abstract/resumen
                abstract = self._extract_abstract(full_text)
                if abstract:
                    doc['resumen_abstract'] = normalize_text(abstract)
                
                # Intentar extraer keywords
                keywords = self._extract_keywords(full_text)
                if keywords:
                    doc['keywords'] = normalize_text(keywords)
                
                # Intentar extraer información de publicación
                journal = self._extract_journal(full_text)
                if journal:
                    doc['lugar_publicacion_entrega'] = normalize_text(journal)
                
                # Intentar extraer páginas
                pages = self._extract_pages(full_text)
                if pages:
                    doc['paginas'] = pages
                
                # Intentar extraer volumen
                volume = self._extract_volume(full_text)
                if volume:
                    doc['volumen_edicion'] = volume
                
        except Exception as e:
            print(f"Error extracting PDF: {e}")
        
        return doc
    
    def _extract_title(self, pdf, full_text: str) -> Optional[str]:
        """Extrae título del PDF"""
        # Intentar obtener título de metadata primero
        try:
            if hasattr(pdf, 'metadata') and pdf.metadata:
                title = pdf.metadata.get('Title')
                if title and len(title) > 10:
                    return title
        except:
            pass
        
        # Si no hay metadata, buscar en el texto
        if pdf.pages:
            first_page = pdf.pages[0]
            first_page_text = first_page.extract_text() or ""
            
            # Excluir patrones comunes de headers/footers
            exclude_patterns = [
                r'^Vol\.?\s*\d+',  # "Vol. 537"
                r'^\d+:\s*\d+-\d+',  # "247-263"
                r'MARINE ECOLOGY|JOURNAL OF|PROGRESS SERIES',  # Nombres de revistas comunes
                r'©\s+',  # Copyright
                r'@.*\.(com|edu|org)',  # Emails
            ]
            
            # Buscar líneas grandes o en negrita (heurística: primeras líneas significativas)
            lines = first_page_text.split('\n')[:20]  # Primeras 20 líneas
            for line in lines:
                line = line.strip()
                # Título generalmente tiene cierta longitud y no es solo números
                if 15 < len(line) < 300:
                    # Excluir si coincide con patrones de header/footer
                    should_exclude = False
                    for pattern in exclude_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            should_exclude = True
                            break
                    
                    if should_exclude:
                        continue
                    
                    # No debe ser autor, año, o metadata común
                    if (not re.match(r'^\d{4}$', line) and 
                        'doi:' not in line.lower() and
                        not line.lower().startswith('author') and
                        not line.lower().startswith('abstract') and
                        not re.match(r'^[A-Z][a-z]+,?\s*[A-Z]\.', line) and
                        '@' not in line):  # No debe contener email
                        # Intentar agregar espacios entre palabras que están juntas
                        if re.search(r'[a-z][A-Z]', line):  # Hay minúscula seguida de mayúscula
                            line = re.sub(r'([a-z])([A-Z])', r'\1 \2', line)
                        return line
        
        return None
    
    def _extract_authors(self, text: str) -> Optional[str]:
        """Extrae autores del texto"""
        # Excluir emails, copyrights, etc.
        exclude_patterns = [
            r'@.*\.(com|edu|org|ca|uk)',
            r'©\s+',
            r'Copyright',
            r'Inter-Research',
            r'Fisheries and Oceans',
        ]
        
        # Buscar sección de autores común
        author_sections = [
            r'Author[s]?[:\s]+(.+?)(?:\n\n|\nAbstract|\nSummary|\nKeywords|^Abstract|^Summary)',
            r'^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*(?:,\s*[A-Z]\.?)+,?\s*(?:and\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*(?:,\s*[A-Z]\.?)*)',
        ]
        
        for pattern in author_sections:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                authors = match.group(1).strip()
                # Validar que no contenga patrones excluidos
                should_exclude = False
                for exclude_pattern in exclude_patterns:
                    if re.search(exclude_pattern, authors, re.IGNORECASE):
                        should_exclude = True
                        break
                
                if should_exclude:
                    continue
                
                # Limpiar y validar
                authors = re.sub(r'\s+', ' ', authors)
                if len(authors) > 5 and not authors.lower().startswith('abstract'):
                    return normalize_text(authors)
        
        # Buscar después del título, antes del abstract
        abstract_pos = re.search(r'\n\s*Abstract|\n\s*Summary', text, re.IGNORECASE)
        if abstract_pos:
            # Buscar líneas entre el inicio y el abstract que parezcan autores
            before_abstract = text[:abstract_pos.start()]
            lines = before_abstract.split('\n')[-5:]  # Últimas 5 líneas antes del abstract
            for line in lines:
                line = line.strip()
                # Validar que no contenga patrones excluidos
                should_exclude = False
                for exclude_pattern in exclude_patterns:
                    if re.search(exclude_pattern, line, re.IGNORECASE):
                        should_exclude = True
                        break
                
                if should_exclude:
                    continue
                
                # Si tiene formato de autor (nombres con iniciales o apellidos)
                if (re.search(r'[A-Z][a-z]+\s+[A-Z]\.', line) or 
                    re.search(r'[A-Z][a-z]+,\s*[A-Z]', line)):
                    if 10 < len(line) < 200:
                        return normalize_text(line)
        
        return None
    
    def _extract_abstract(self, text: str) -> Optional[str]:
        """Extrae abstract o resumen"""
        # Buscar sección de abstract
        patterns = [
            r'Abstract[:\s]+(.+?)(?:\n\n|Keywords|Introduction|Resumen)',
            r'Resumen[:\s]+(.+?)(?:\n\n|Palabras|Introducción)',
            r'SUMMARY[:\s]+(.+?)(?:\n\n|Keywords|Introduction)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                # Limitar longitud razonable
                if 50 < len(abstract) < 2000:
                    return abstract
        
        return None
    
    def _extract_keywords(self, text: str) -> Optional[str]:
        """Extrae keywords o palabras clave"""
        patterns = [
            r'Keywords?[:\s]+(.+?)(?:\n\n|Abstract|Introduction|1\.)',
            r'Palabras\s+clave[:\s]+(.+?)(?:\n\n|Resumen|Introducción|1\.)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                keywords = match.group(1).strip()
                # Limpiar y limitar
                keywords = re.sub(r'\s+', ' ', keywords)
                if 5 < len(keywords) < 500:
                    return keywords
        
        return None
    
    def _extract_journal(self, text: str) -> Optional[str]:
        """Extrae nombre de revista"""
        # Buscar en header/footer o metadata
        patterns = [
            r'Published\s+in[:\s]+(.+?)(?:\n|,|\.)',
            r'Journal\s+of[:\s]+(.+?)(?:\n|,|\.)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return normalize_text(match.group(1))
        
        return None
    
    def _extract_pages(self, text: str) -> Optional[str]:
        """Extrae páginas"""
        # Buscar en metadata
        pattern = r'Pages?[:\s]+(\d+[-\u2013\u2014]\d+|\d+)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_volume(self, text: str) -> Optional[str]:
        """Extrae volumen"""
        pattern = r'Volume[:\s]+(\d+)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None

