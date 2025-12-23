import re
import pdfplumber
import logging
from typing import Dict, Optional
from io import BytesIO
from app.services.grobid_service import GrobidService
from app.utils.text_processing import extract_doi, extract_year, extract_isbn_issn, normalize_text
from app.utils.patterns import BiblioPatterns

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Servicio para extraer información bibliográfica de PDFs"""
    
    def __init__(self):
        self.grobid_service = GrobidService()
    
    def extract(self, pdf_content: bytes) -> Dict[str, Optional[str]]:
        """
        Extrae información bibliográfica de un PDF
        Estrategia: Intentar GROBID primero (si está disponible), luego fallback a regex
        """
        doc = {}
        
        # Intentar GROBID primero (opcional)
        if self.grobid_service.use_grobid:
            grobid_header = self.grobid_service.extract_header_from_pdf(pdf_content)
            if grobid_header:
                # Mapear campos de GROBID a formato interno
                if 'title' in grobid_header:
                    doc['titulo_original'] = normalize_text(grobid_header['title'])
                if 'authors' in grobid_header:
                    doc['autores'] = grobid_header['authors']
                if 'year' in grobid_header:
                    doc['ano'] = grobid_header['year']
                if 'doi' in grobid_header:
                    doc['doi'] = grobid_header['doi']
                if 'abstract' in grobid_header:
                    doc['resumen_abstract'] = normalize_text(grobid_header['abstract'])
                
                # Si GROBID extrajo información suficiente, usarla como base
                if doc.get('titulo_original') or doc.get('autores'):
                    logger.info("Usando metadata de GROBID como base")
                    # Continuar con extracción adicional usando regex para campos faltantes
                    # pero priorizar datos de GROBID
        
        # Continuar con extracción regex (complementa o reemplaza según lo que haya)
        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                # Extraer texto de todas las páginas
                full_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        # Corregir encoding común de PDFs
                        # Algunos PDFs tienen problemas con caracteres especiales
                        try:
                            # Intentar decodificar correctamente
                            if isinstance(page_text, bytes):
                                page_text = page_text.decode('utf-8', errors='replace')
                            full_text += page_text + "\n"
                        except:
                            full_text += str(page_text) + "\n"
                
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
                # Solo si GROBID no lo extrajo
                if 'titulo_original' not in doc:
                    title = self._extract_title(pdf, full_text)
                    if title:
                        doc['titulo_original'] = normalize_text(title)
                
                # Intentar extraer autores (generalmente después del título o en metadata)
                # Solo si GROBID no los extrajo
                if 'autores' not in doc:
                    authors = self._extract_authors(full_text)
                    if authors:
                        doc['autores'] = authors
                
                # Intentar extraer abstract/resumen
                # Solo si GROBID no lo extrajo
                if 'resumen_abstract' not in doc:
                    abstract = self._extract_abstract(full_text)
                    if abstract:
                        doc['resumen_abstract'] = normalize_text(abstract)
                
                # Intentar extraer keywords
                keywords = self._extract_keywords(full_text)
                if keywords:
                    # Normalizar espacios entre palabras concatenadas
                    from app.utils.text_processing import normalize_text_spacing
                    keywords = normalize_text_spacing(keywords)
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
                r'MARINE ECOLOGY|JOURNAL OF|PROGRESS SERIES|PLOS ONE',  # Nombres de revistas comunes
                r'©\s+',  # Copyright
                r'@.*\.(com|edu|org)',  # Emails
                r'^RESEARCH ARTICLE|^REVIEW ARTICLE',  # Tipos de artículo
            ]
            
            # Buscar título: generalmente es la línea más larga y significativa antes de los autores
            lines = first_page_text.split('\n')[:30]  # Primeras 30 líneas
            
            # Buscar línea que parezca título (larga, no es autor, no es metadata)
            title_candidates = []
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Excluir líneas muy cortas o muy largas
                if len(line) < 20 or len(line) > 600:
                    continue
                # Excluir si coincide con patrones de header/footer
                should_exclude = False
                for pattern in exclude_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        should_exclude = True
                        break
                
                if should_exclude:
                    continue
                
                # No debe ser autor (patrón: Apellido, Inicial.)
                if re.match(BiblioPatterns.AUTHOR_FULL, line):
                    continue
                
                # No debe ser año solo
                if re.match(r'^\d{4}$', line):
                    continue
                
                # No debe contener email
                if '@' in line:
                    continue
                
                # No debe ser "doi:" o similar
                if 'doi:' in line.lower() and len(line) < 50:
                    continue
                
                # No debe empezar con "Author", "Abstract", etc.
                if re.match(r'^(Author|Abstract|Summary|Keywords|Received|Accepted|Published|Editor|Citation|RESEARCH ARTICLE|REVIEW ARTICLE)', line, re.IGNORECASE):
                    continue
                
                # Si la línea es significativamente larga y parece título, agregarla como candidato
                if len(line) > 30:
                    # Intentar agregar espacios entre palabras que están juntas
                    if re.search(r'[a-z][A-Z]', line):  # Hay minúscula seguida de mayúscula
                        line = re.sub(r'([a-z])([A-Z])', r'\1 \2', line)
                    title_candidates.append((i, line, len(line)))
            
            # Si hay candidatos, tomar el primero (más probable que sea el título)
            if title_candidates:
                # Ordenar por posición (más arriba = mejor) y longitud
                title_candidates.sort(key=lambda x: (x[0], -x[2]))
                title = title_candidates[0][1]
                
                # Si el título está cortado, intentar buscar líneas siguientes que lo continúen
                title_idx = title_candidates[0][0]
                if title_idx + 1 < len(lines):
                    # Verificar si la siguiente línea es continuación del título
                    next_line = lines[title_idx + 1].strip()
                    # Si la siguiente línea no es autor ni metadata, podría ser continuación
                    if (len(next_line) > 10 and 
                        not re.match(r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?,\s*[A-Z]\.', next_line) and
                        not re.match(r'^\d{4}$', next_line) and
                        '@' not in next_line and
                        'doi:' not in next_line.lower() and
                        not re.match(r'^(Author|Abstract|Summary|Keywords)', next_line, re.IGNORECASE)):
                        # Podría ser continuación del título
                        title = title + " " + next_line
                
                return title
        
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
        # Patrón mejorado para detectar nombres de autores
        abstract_pos = re.search(r'\n\s*Abstract|\n\s*Summary', text, re.IGNORECASE)
        if abstract_pos:
            # Buscar líneas entre el inicio y el abstract que parezcan autores
            before_abstract = text[:abstract_pos.start()]
            lines = before_abstract.split('\n')
            
            # Buscar líneas que tengan patrón de autores: Apellido, Inicial., Apellido, Inicial.
            author_lines = []
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Excluir líneas que son claramente parte del título o metadata
                if (len(line) < 5 or len(line) > 600 or
                    '@' in line or
                    'doi:' in line.lower() or
                    re.match(r'^\d{4}$', line) or
                    re.match(r'^(Author|Abstract|Summary|Keywords|Received|Accepted|Published|Editor|Citation|RESEARCH ARTICLE|REVIEW ARTICLE)', line, re.IGNORECASE)):
                    continue
                
                # Patrón de autor: Apellido, Inicial. (puede tener múltiples autores)
                # Ejemplo: "Porobic, J., Fulton, E.A., Parada, C."
                # También aceptar formato: "Porobic J, Fulton EA" (sin punto después de inicial)
                author_patterns = [
                    r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?,\s*[A-Z]\.',  # "Apellido, Inicial."
                    r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?,\s*[A-Z]',     # "Apellido, Inicial" (sin punto)
                    r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-Z]\.',                                    # "Apellido Inicial." (sin coma)
                ]
                
                is_author_line = False
                for pattern in author_patterns:
                    if re.match(pattern, line):
                        is_author_line = True
                        break
                
                if is_author_line:
                    # Validar que no es parte del título (no debe contener palabras comunes del título)
                    should_exclude = False
                    for exclude_pattern in exclude_patterns:
                        if re.search(exclude_pattern, line, re.IGNORECASE):
                            should_exclude = True
                            break
                    
                    # Excluir si contiene palabras comunes de títulos (pero no demasiado restrictivo)
                    title_words = ['ecosystem', 'case of', 'impact', 'study', 'analysis', 'evaluation']
                    if any(word in line.lower() for word in title_words) and len(line) > 50:
                        should_exclude = True
                    
                    if not should_exclude and len(line) > 10 and len(line) < 500:
                        author_lines.append((i, line))
            
            if author_lines:
                # Ordenar por posición (más arriba = mejor)
                author_lines.sort(key=lambda x: x[0])
                # Unir múltiples líneas de autores
                authors = ' '.join([line for _, line in author_lines])
                authors = re.sub(r'\s+', ' ', authors)
                # Limpiar comas y puntos finales
                authors = authors.rstrip(',. ')
                return normalize_text(authors)
        
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
                # Limpiar saltos de línea
                keywords = re.sub(r'\s+', ' ', keywords)
                
                # Si las keywords están separadas por comas, agregar espacio después de cada coma
                if ',' in keywords:
                    keywords = re.sub(r',\s*', ', ', keywords)
                
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

