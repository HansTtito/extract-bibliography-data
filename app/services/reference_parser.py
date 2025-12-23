import re
from typing import Dict, Optional, List
from app.utils.text_processing import extract_doi, extract_year, extract_isbn_issn, normalize_text
from app.utils.patterns import BiblioPatterns, TextNormalizer


class ReferenceParser:
    """Parser para extraer información de referencias bibliográficas en texto libre"""
    
    def parse(self, reference_text: str) -> Dict[str, Optional[str]]:
        """Parsea una referencia bibliográfica y extrae información básica"""
        doc = {}
        
        # Normalizar texto y limpiar "REFERENCES" si está al inicio
        text = reference_text.strip()
        text = TextNormalizer.clean_references_header(text)
        
        # Extraer DOI
        doi = extract_doi(text)
        if doi:
            doc['doi'] = doi
        
        # MEJORADO: Extraer año con método más preciso
        year = self._extract_year_from_reference(text)
        if not year:
            # Fallback: usar método general
            year = extract_year(text)
        if year:
            doc['ano'] = year
        
        # Extraer ISBN/ISSN
        isbn_issn = extract_isbn_issn(text)
        if isbn_issn:
            doc['isbn_issn'] = isbn_issn
        
        # Intentar extraer autores (patrón común: Apellido, Inicial., Apellido, Inicial. (Año))
        authors = self._extract_authors(text)
        if authors:
            doc['autores'] = authors
        
        # Intentar extraer título (generalmente después de los autores y antes del año o revista)
        title = self._extract_title(text)
        if title:
            doc['titulo_original'] = normalize_text(title)
        
        # Detectar tipo de documento
        if re.search(r'\bIn:\s*', text, re.IGNORECASE):
            doc['tipo_documento'] = 'Capítulo de libro'
            # Para capítulos, el lugar de publicación es el título del libro
            book_title = self._extract_book_title(text)
            if book_title:
                doc['lugar_publicacion_entrega'] = normalize_text(book_title)
        else:
            # Intentar extraer revista/lugar de publicación
            journal = self._extract_journal(text)
            if journal:
                doc['lugar_publicacion_entrega'] = normalize_text(journal)
                doc['tipo_documento'] = 'Artículo en revista científica'
        
        # Intentar extraer páginas
        pages = self._extract_pages(text)
        if pages:
            doc['paginas'] = pages
        
        # Intentar extraer volumen
        volume = self._extract_volume(text)
        if volume:
            doc['volumen_edicion'] = volume
        
        # Intentar extraer link (URL)
        link = self._extract_link(text)
        if link:
            doc['link'] = link
        
        return doc
    
    def _extract_year_from_reference(self, text: str) -> Optional[int]:
        """
        Extrae año de la referencia con prioridad:
        1. Año entre paréntesis: (2009)
        2. Año seguido de punto: 2009.
        3. Año en cualquier posición válida
        """
        # Prioridad 1: Año entre paréntesis (más confiable)
        match = re.search(r'\((\d{4})\)', text)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2030:
                return year
        
        # Prioridad 2: Año seguido de punto y espacio (formato común)
        match = re.search(r'(\d{4})\.\s+[A-Z]', text)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2030:
                return year
        
        # Prioridad 3: Año seguido de punto sin espacio
        match = re.search(r'(\d{4})\.', text)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2030:
                return year
        
        # Prioridad 4: Cualquier año válido en el texto
        match = re.search(BiblioPatterns.YEAR_FULL, text)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2030:
                return year
        
        return None
    
    def _extract_authors(self, text: str) -> Optional[str]:
        """
        Extrae TODOS los autores de la referencia
        MEJORADO: Captura múltiples autores correctamente
        """
        # Limpiar texto: remover "REFERENCES" si está al inicio
        text = TextNormalizer.clean_references_header(text)
        
        # MEJORADO: Buscar año entre paréntesis primero (más confiable)
        # Formato: "Autor, I. (2009). Título..."
        year_match = re.search(r'\((\d{4})\)', text)
        if not year_match:
            # Fallback: buscar año sin paréntesis
            year_match = re.search(BiblioPatterns.YEAR_SHORT, text)
            if not year_match:
                return None
        
        # Autores están ANTES del año
        authors_text = text[:year_match.start()].strip()
        
        # Validar que no empiece con palabras inválidas
        if BiblioPatterns.is_reference_section(authors_text) or BiblioPatterns.is_section(authors_text):
            return None
        
        # MEJORADO: Capturar TODOS los autores con diferentes formatos
        # Formato 1: "Apellido, Inicial., Apellido, Inicial., and Apellido, Inicial."
        # Formato 2: "Apellido, Inicial., Apellido, Inicial., Apellido, Inicial."
        
        # Normalizar conectores
        authors_text = authors_text.replace(' and ', ', ').replace(' y ', ', ')
        
        # Patrón mejorado: captura secuencia completa de autores
        # Captura: "Apellido, I." o "Apellido, I.I." (múltiples iniciales)
        author_pattern = r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?,\s*[A-Z]\.(?:\s*[A-Z]\.)*)'
        
        authors_found = re.findall(author_pattern, authors_text)
        
        if authors_found:
            # Unir todos los autores encontrados
            authors = ', '.join(authors_found)
            # Limpiar espacios extra
            authors = TextNormalizer.clean_multiple_spaces(authors)
            # Validar que tenga al menos un autor completo
            if re.search(BiblioPatterns.AUTHOR_VALID, authors):
                return normalize_text(authors)
        
        # Patrón alternativo: buscar hasta el año, validando formato de autor
        if ',' in authors_text and len(authors_text) > 5:
            # Verificar que tenga formato de autor (al menos un "Apellido, Inicial")
            if re.search(r'[A-Z][a-z]+,\s*[A-Z]', authors_text):
                authors = authors_text.rstrip(',. ')
                authors = TextNormalizer.clean_references_header(authors)
                authors = TextNormalizer.clean_multiple_spaces(authors)
                if authors:
                    return normalize_text(authors)
        
        return None
    
    def _extract_title(self, text: str) -> Optional[str]:
        """
        Extrae título del documento
        MEJORADO: Estrategia más simple y robusta
        """
        # 1. Buscar título entre comillas (más confiable)
        quoted = re.search(BiblioPatterns.TITLE_QUOTED, text)
        if quoted:
            return quoted.group(1)
        
        # 2. Buscar año para delimitar
        year_match = re.search(r'\((\d{4})\)', text)
        if not year_match:
            year_match = re.search(r'(\d{4})\.\s', text)
        
        if not year_match:
            return None
        
        # 3. Título está después del año y punto
        # Formato: "(2009). Título aquí. Revista Volumen"
        after_year = text[year_match.end():].strip()
        
        # Buscar punto después del año
        if not after_year.startswith('.'):
            # Si no empieza con punto, buscar el primer punto
            dot_match = re.search(r'\.\s+', after_year)
            if dot_match:
                after_year = after_year[dot_match.end():]
        else:
            # Quitar punto inicial
            after_year = after_year.lstrip('. ')
        
        # 4. CLAVE: Título termina cuando encuentra:
        #    - Punto + Palabra corta (1-2 palabras) + Número
        #    - Esto indica: "Título. Revista Vol"
        
        # Patrón: encuentra ". Palabra(s) Número"
        # Ej: ". J. Mar. Syst. 78" o ". Marine Ecology 123"
        title_end = re.search(
            r'\.\s+([A-Z][\w\s\.\,&-]{1,50}?)\s+\d+',
            after_year
        )
        
        if title_end:
            # Tomar solo hasta antes del punto que precede a la revista
            title = after_year[:title_end.start()].strip()
            return title if len(title) > 10 else None
        
        # 5. Fallback: tomar hasta el primer punto
        first_dot = re.search(r'\.\s', after_year)
        if first_dot:
            title = after_year[:first_dot.start()].strip()
            return title if len(title) > 10 else None
        
        return None
    
    def _extract_journal(self, text: str) -> Optional[str]:
        """
        Extrae nombre de revista
        MEJORADO: Más simple y directo
        """
        # 1. Primero extraer el título para saber dónde buscar
        title = self._extract_title(text)
        if not title:
            return None
        
        # 2. Buscar dónde termina el título en el texto
        title_pos = text.find(title)
        if title_pos == -1:
            return None
        
        # 3. Revista está después del título
        after_title = text[title_pos + len(title):].strip()
        
        # 4. CLAVE: Revista es lo que está entre el punto y el número (volumen)
        # Formato: ". Revista Volumen"
        # Ej: ". J. Mar. Syst. 78" → "J. Mar. Syst."
        
        journal_match = re.search(
            r'\.\s+([A-Z][\w\s\.\,&-]{1,50}?)\s+(\d+)',
            after_title
        )
        
        if journal_match:
            journal = journal_match.group(1).strip()
            # Limpiar punto final si existe
            journal = journal.rstrip('.,')
            
            # Validar longitud razonable
            if 3 < len(journal) < 60:
                return journal
        
        return None
    
    def _extract_pages(self, text: str) -> Optional[str]:
        """Extrae rango de páginas"""
        # Patrones comunes: pp. 123-456, p. 123, 123-456, 123–456
        patterns = [
            r'pp?\.\s*(\d+[-\u2013\u2014]\d+)',
            r'(\d+[-\u2013\u2014]\d+)',
            r'pp?\.\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1) if len(match.groups()) > 0 else match.group(0)
        
        return None
    
    def _extract_volume(self, text: str) -> Optional[str]:
        """Extrae volumen o número"""
        # Patrones: Vol. 5, Volume 5, v. 5, 5(3)
        patterns = [
            r'[Vv]ol\.?\s*(\d+)',
            r'[Vv]olume\s*(\d+)',
            r'v\.\s*(\d+)',
            r'(\d+)\((\d+)\)',  # Volumen(Número)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) > 1:
                    return f"{match.group(1)}({match.group(2)})"
                return match.group(1)
        
        return None
    
    def _extract_link(self, text: str) -> Optional[str]:
        """Extrae URL o link"""
        url_pattern = r'https?://[^\s\)]+'
        match = re.search(url_pattern, text)
        if match:
            return match.group(0)
        return None
    
    def _extract_book_title(self, text: str) -> Optional[str]:
        """Extrae título del libro para capítulos"""
        # Buscar "In:" seguido de editores y luego el título del libro
        in_match = re.search(r'\bIn:\s*', text, re.IGNORECASE)
        if not in_match:
            return None
        
        # Después de "In:" vienen los editores, luego el título del libro
        after_in = text[in_match.end():]
        
        # Buscar editores (formato: Apellido, Inicial. (Eds.),)
        editors_match = re.search(r'\(Eds?\.\)', after_in, re.IGNORECASE)
        if editors_match:
            # Título del libro está después de los editores
            after_editors = after_in[editors_match.end():].strip()
            # Limpiar comas y espacios iniciales
            after_editors = re.sub(r'^[,\s]+', '', after_editors)
            
            # El título del libro generalmente termina antes de "pp." o un punto seguido de número
            # O antes de "Available from:"
            end_patterns = [
                r'\s+pp\.',
                r'\s+Available\s+from:',
                r'\.\s+\d{4}',
            ]
            
            for pattern in end_patterns:
                end_match = re.search(pattern, after_editors, re.IGNORECASE)
                if end_match:
                    book_title = after_editors[:end_match.start()].strip()
                    # Limpiar punto final si existe
                    book_title = book_title.rstrip('.')
                    if len(book_title) > 10:
                        return book_title
            
            # Si no hay patrón de fin claro, tomar hasta el primer punto seguido de espacio y mayúscula
            # o hasta "pp."
            title_match = re.match(r'^(.+?)(?:\.\s+[A-Z]|pp\.)', after_editors)
            if title_match:
                book_title = title_match.group(1).strip().rstrip('.')
                if len(book_title) > 10:
                    return book_title
        
        return None

