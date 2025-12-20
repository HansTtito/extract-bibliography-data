import re
from typing import Dict, Optional, List
from app.utils.text_processing import extract_doi, extract_year, extract_isbn_issn, normalize_text


class ReferenceParser:
    """Parser para extraer información de referencias bibliográficas en texto libre"""
    
    def parse(self, reference_text: str) -> Dict[str, Optional[str]]:
        """Parsea una referencia bibliográfica y extrae información básica"""
        doc = {}
        
        # Normalizar texto
        text = reference_text.strip()
        
        # Extraer DOI
        doi = extract_doi(text)
        if doi:
            doc['doi'] = doi
        
        # Extraer año
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
    
    def _extract_authors(self, text: str) -> Optional[str]:
        """Extrae autores de la referencia"""
        # Patrón común: Apellido, Inicial., Apellido, Inicial., Año
        # Ejemplo: "Nandor, G.F., Longwill, J.R., Webb, D.L., 2010"
        
        # Buscar año para delimitar dónde terminan los autores
        year_match = re.search(r'\b(19|20)\d{2}\b', text)
        if not year_match:
            return None
        
        # Autores están antes del año
        authors_text = text[:year_match.start()].strip()
        
        # Patrón para autores: Apellido, Inicial., Apellido, Inicial.
        # Puede terminar en coma o punto antes del año
        author_pattern = r'^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?(?:,\s*[A-Z]\.?)+,?\s*)+'
        match = re.match(author_pattern, authors_text)
        if match:
            authors = match.group(0).rstrip(',. ')
            # Validar que tenga al menos un autor completo (Apellido, Inicial.)
            if re.search(r'[A-Z][a-z]+,\s*[A-Z]\.', authors):
                return normalize_text(authors)
        
        # Patrón alternativo: buscar hasta el año, validando formato de autor
        if ',' in authors_text and len(authors_text) > 5:
            # Verificar que tenga formato de autor (al menos un "Apellido, Inicial")
            if re.search(r'[A-Z][a-z]+,\s*[A-Z]', authors_text):
                return normalize_text(authors_text.rstrip(',. '))
        
        return None
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extrae título del documento"""
        # Buscar título entre comillas
        quoted = re.search(r'["\'](.+?)["\']', text)
        if quoted:
            return quoted.group(1)
        
        # Detectar si es capítulo de libro (tiene "In:")
        in_pos = re.search(r'\bIn:\s*', text, re.IGNORECASE)
        
        # Buscar año
        year_pos = re.search(r'\b(19|20)\d{2}\b', text)
        if not year_pos:
            return None
        
        year_end = year_pos.end()
        
        # El título SIEMPRE está DESPUÉS del año (formato estándar: Autores, Año. Título...)
        # Buscar el punto después del año que separa año de título
        after_year = text[year_end:].strip()
        
        # Si es capítulo de libro, el título está entre el año. y "In:"
        if in_pos and in_pos.start() > year_end:
            # Título del capítulo está entre año. y "In:"
            title_candidate = text[year_end:in_pos.start()].strip()
            # Limpiar punto inicial y espacios
            title_candidate = re.sub(r'^[.\s]+', '', title_candidate)
            # Validar que no sea formato de autor
            if len(title_candidate) > 10 and not re.match(r'^[A-Z][a-z]+,\s*[A-Z]', title_candidate):
                return title_candidate
        else:
            # Artículo normal: título después del año y punto
            # Buscar el primer punto después del año (separador año-título)
            dot_after_year = re.search(r'\.\s+', after_year)
            if dot_after_year:
                # Título está después del punto
                title_start = year_end + dot_after_year.end()
                title_text = text[title_start:].strip()
                
                # El título termina generalmente en un punto seguido de espacio y mayúscula (inicio de revista)
                # O en "In:" para capítulos
                # O en "pp." para páginas
                # Patrón más específico: punto seguido de espacio y palabra corta en mayúsculas (revista abreviada)
                # Ejemplo: "Biol. Conserv." o "J. Exp. Mar. Biol. Ecol."
                
                title_end_patterns = [
                    r'\.\s+[A-Z][a-z]*\.\s+[A-Z]',  # Punto seguido de abreviatura de revista (ej: "Biol. Conserv")
                    r'\.\s+[A-Z][a-z]+\s+\d+',  # Punto seguido de nombre de revista y volumen
                    r'\.\s+In:',  # Capítulo
                    r'\.\s+pp\.',  # Páginas
                    r'\.\s+Available',  # Link
                ]
                
                title_end_pos = len(title_text)
                for pattern in title_end_patterns:
                    match = re.search(pattern, title_text)
                    if match and match.start() < title_end_pos:
                        title_end_pos = match.start()
                
                if title_end_pos < len(title_text):
                    title_candidate = title_text[:title_end_pos].strip()
                else:
                    # Buscar el último punto que probablemente termina el título
                    # El título generalmente termina en punto, luego viene la revista
                    # Buscar patrón: punto seguido de espacio y palabra corta en mayúsculas
                    last_dot_match = list(re.finditer(r'\.\s+', title_text))
                    if last_dot_match:
                        # Tomar hasta el último punto (probable fin del título)
                        last_dot = last_dot_match[-1]
                        # Verificar que después del punto hay algo que parece revista
                        after_last_dot = title_text[last_dot.end():].strip()
                        if re.match(r'^[A-Z]', after_last_dot):  # Empieza con mayúscula (revista)
                            title_candidate = title_text[:last_dot.start()].strip()
                        else:
                            # Si no, tomar hasta el primer punto
                            title_match = re.match(r'^(.+?)\.\s+', title_text)
                            title_candidate = title_match.group(1).strip() if title_match else title_text.strip()
                    else:
                        # Tomar todo hasta el final si no hay patrón claro
                        title_candidate = title_text.strip()
                
                # Limpiar y validar
                title_candidate = re.sub(r'^[.,;:\s]+', '', title_candidate)
                # Validar que no sea formato de autor (no debe empezar con "Apellido, Inicial")
                if (len(title_candidate) > 10 and 
                    not re.match(r'^[A-Z][a-z]+,\s*[A-Z]', title_candidate) and
                    not re.search(r'^[A-Z][a-z]+,\s*[A-Z][a-z]+,\s*[A-Z]', title_candidate)):
                    return title_candidate
        
        return None
    
    def _extract_journal(self, text: str) -> Optional[str]:
        """Extrae nombre de revista o lugar de publicación"""
        # El formato es: Título. Revista Volumen, Páginas
        # La revista viene DESPUÉS del título, generalmente seguida de un número (volumen)
        
        # Primero, intentar encontrar dónde termina el título
        title = self._extract_title(text)
        if title:
            # Buscar el título en el texto para saber dónde termina
            title_pos = text.find(title)
            if title_pos != -1:
                # Buscar después del título
                after_title = text[title_pos + len(title):].strip()
                # La revista generalmente viene después de un punto y espacio
                # Formato: "Título. Revista Volumen" o "Título. Revista, Volumen"
                journal_match = re.search(r'\.\s+([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s&,\.]+?)(?:,\s*\d+|\s+\d+)', after_title)
                if journal_match:
                    journal = journal_match.group(1).strip()
                    # Limpiar punto final si existe
                    journal = journal.rstrip('.')
                    # Validar que no sea muy largo (las revistas suelen ser cortas)
                    if 2 < len(journal) < 100:
                        return journal
        
        # Fallback: buscar patrón común de revista después del año
        # Formato: "Año. Título. Revista Volumen"
        year_match = re.search(r'\d{4}\.', text)
        if year_match:
            # Buscar después del título (que termina en punto)
            # Buscar patrón: ". Revista" seguido de número
            after_year = text[year_match.end():]
            # Buscar el último punto antes del volumen (ese punto termina el título)
            # Luego viene la revista
            journal_pattern = r'\.\s+([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ\s&,\.]+?)(?:,\s*\d+|\s+\d+)'
            journal_match = re.search(journal_pattern, after_year)
            if journal_match:
                journal = journal_match.group(1).strip().rstrip('.')
                # Validar que no sea muy largo y que parezca nombre de revista
                if 2 < len(journal) < 100 and not re.search(r'\b(management|strategy|evaluation|applied|to|the|conservation|of|an|endangered|population|subject|incidental|take)\b', journal, re.IGNORECASE):
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

