import re
from typing import Dict, Optional, List
from app.utils.text_processing import extract_doi, extract_year, extract_isbn_issn, normalize_text
from app.utils.patterns import BiblioPatterns, TextNormalizer, ExtractionPatterns


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
        2. Año seguido de punto/coma: 2009. o 2009;
        3. Año en cualquier posición válida (ignorando años en títulos)
        """
        # Buscar años con diferentes formatos (en orden de confiabilidad)
        patterns = [
            ExtractionPatterns.YEAR_PARENTHESIS,      # (2009) - más confiable
            ExtractionPatterns.YEAR_SEMICOLON,        # 2009; - común con volumen
            ExtractionPatterns.YEAR_DOT_SPACE,        # 2009. Title
            ExtractionPatterns.YEAR_DOT,              # 2009.
            ExtractionPatterns.YEAR_COMMA,            # 2009,
        ]
        
        # Buscar con patrones específicos primero
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                year = int(match.group(1))
                if 1900 <= year <= 2030:
                    return year
        
        # Último recurso: buscar cualquier año, pero IGNORAR años precedidos por palabras
        # como "año", "year" que probablemente son parte del contenido/título
        all_years = re.finditer(BiblioPatterns.YEAR_FULL, text)
        for match in all_years:
            # Verificar que no esté precedido por palabras que indican que es contenido
            start_pos = match.start()
            if start_pos > 5:
                # Buscar 10 caracteres antes
                context_before = text[max(0, start_pos - 10):start_pos].lower()
                # Si viene después de "año", "year", ignorar este año
                if any(word in context_before for word in ['año', 'year', 'desde', 'between']):
                    continue
            
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
        
        # MEJORADO: Buscar año con diferentes formatos (en orden de confiabilidad)
        # Formato 1: "(2009)" - más confiable
        year_match = re.search(ExtractionPatterns.YEAR_PARENTHESIS, text)
        
        if not year_match:
            # Formato 2: "2009;" - común con volumen/páginas
            year_match = re.search(ExtractionPatterns.YEAR_SEMICOLON, text)
        
        if not year_match:
            # Formato 3: "2009." - estándar
            year_match = re.search(ExtractionPatterns.YEAR_DOT, text)
        
        if not year_match:
            # Formato 4: "2009," - menos común
            year_match = re.search(ExtractionPatterns.YEAR_COMMA, text)
        
        if not year_match:
            # Fallback: cualquier año de 4 dígitos
            year_match = re.search(BiblioPatterns.YEAR_FULL, text)
            if not year_match:
                return None
        
        # Autores están ANTES del año
        authors_text = text[:year_match.start()].strip()
        
        # Validar que no empiece con palabras inválidas
        if BiblioPatterns.is_reference_section(authors_text) or BiblioPatterns.is_section(authors_text):
            return None
        
        # CLAVE: Los autores terminan en el PRIMER punto seguido de espacio
        # Esto separa autores del título: "Guerrero A, Arana P. Size structure..."
        # Los autores son: "Guerrero A, Arana P"
        first_period = re.search(r'\.\s+', authors_text)
        if first_period:
            # Tomar solo hasta el primer punto
            authors_text = authors_text[:first_period.start()].strip()
        
        # Si no hay punto, pero el texto es muy largo (>200 chars), probablemente incluye título
        # En ese caso, tomar solo los primeros ~150 caracteres
        if len(authors_text) > 200:
            # Buscar una coma cercana al inicio que separe autores
            last_comma = authors_text[:150].rfind(',')
            if last_comma > 0:
                authors_text = authors_text[:last_comma + 1].strip()
        
        # Normalizar conectores y "et al."
        authors_text = authors_text.replace(' and ', ', ').replace(' y ', ', ')
        authors_text = re.sub(r',?\s*et\s+al\.?', '', authors_text)  # Remover "et al."
        
        # Intentar primero con formato estándar: "Apellido, Inicial."
        authors_found = re.findall(ExtractionPatterns.AUTHOR_PATTERN, authors_text)
        
        # Si no encuentra con formato estándar, intentar formato sin coma: "Apellido Inicial"
        if not authors_found or len(authors_found) == 0:
            authors_found = re.findall(ExtractionPatterns.AUTHOR_PATTERN_NO_COMMA, authors_text)
            # Normalizar a formato estándar (agregar comas)
            if authors_found:
                authors_found = [re.sub(r'([a-z]+)\s+([A-Z])', r'\1, \2', author) for author in authors_found]
        
        if authors_found:
            # Unir todos los autores encontrados
            authors = ', '.join(authors_found)
            # Limpiar espacios extra
            authors = TextNormalizer.clean_multiple_spaces(authors)
            # Validar longitud mínima
            if len(authors) > 3:
                return normalize_text(authors)
        
        # Patrón alternativo: tomar todo el texto si parece ser solo autores
        if ',' in authors_text and len(authors_text) < 150:
            # Verificar que tenga formato de autor (al menos un "Apellido, Inicial")
            if re.search(r'[A-Z][a-z]+,?\s*[A-Z]', authors_text):
                authors = authors_text.rstrip(',. ')
                authors = TextNormalizer.clean_references_header(authors)
                authors = TextNormalizer.clean_multiple_spaces(authors)
                if len(authors) > 3:
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
        
        # 2. Buscar año para delimitar (probar diferentes formatos)
        year_match = None
        year_patterns = [
            ExtractionPatterns.YEAR_PARENTHESIS,
            ExtractionPatterns.YEAR_SEMICOLON,
            ExtractionPatterns.YEAR_DOT_SPACE,
            ExtractionPatterns.YEAR_DOT,
            ExtractionPatterns.YEAR_COMMA,
        ]
        
        for pattern in year_patterns:
            year_match = re.search(pattern, text)
            if year_match:
                break
        
        if not year_match:
            return None
        
        # 3. Título está después del año y punto
        # Formato: "(2009). Título aquí. Revista Volumen"
        after_year = text[year_match.end():].strip()
        
        # Buscar punto después del año
        if not after_year.startswith('.'):
            # Si no empieza con punto, buscar el primer punto
            dot_match = re.search(ExtractionPatterns.TITLE_END_DOT, after_year)
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
        title_end = re.search(ExtractionPatterns.TITLE_END_JOURNAL, after_year)
        
        if title_end:
            # Tomar solo hasta antes del punto que precede a la revista
            title = after_year[:title_end.start()].strip()
            return title if len(title) > 10 else None
        
        # 5. Fallback: tomar hasta el primer punto
        first_dot = re.search(ExtractionPatterns.TITLE_END_DOT, after_year)
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
        
        journal_match = re.search(ExtractionPatterns.JOURNAL_VOLUME, after_title)
        
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
        match = re.search(ExtractionPatterns.URL_PATTERN, text)
        if match:
            return match.group(0)
        return None
    
    def _extract_book_title(self, text: str) -> Optional[str]:
        """Extrae título del libro para capítulos"""
        # Buscar "In:" seguido de editores y luego el título del libro
        in_match = re.search(ExtractionPatterns.IN_BOOK, text, re.IGNORECASE)
        if not in_match:
            return None
        
        # Después de "In:" vienen los editores, luego el título del libro
        after_in = text[in_match.end():]
        
        # Buscar editores (formato: Apellido, Inicial. (Eds.),)
        editors_match = re.search(ExtractionPatterns.EDITORS, after_in, re.IGNORECASE)
        if editors_match:
            # Título del libro está después de los editores
            after_editors = after_in[editors_match.end():].strip()
            # Limpiar comas y espacios iniciales
            after_editors = re.sub(r'^[,\s]+', '', after_editors)
            
            # El título del libro generalmente termina antes de "pp." o un punto seguido de número
            # O antes de "Available from:"
            for pattern in ExtractionPatterns.BOOK_TITLE_END:
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

