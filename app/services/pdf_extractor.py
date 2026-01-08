import re
import pdfplumber
import logging
from typing import Dict, Optional
from io import BytesIO
from app.services.grobid_service import GrobidService
from app.services.claude_extractor import ClaudeExtractor
from app.config import settings
from app.utils.text_processing import extract_doi, extract_year, extract_isbn_issn, normalize_text
from app.utils.patterns import BiblioPatterns, ExtractionPatterns, ValidationPatterns, TextNormalizer

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Servicio para extraer información bibliográfica de PDFs"""
    
    def __init__(self):
        self.grobid_service = GrobidService()
        self.claude_extractor = ClaudeExtractor()
        self.claude_extractor = ClaudeExtractor()
    
    def extract(self, pdf_content: bytes) -> Dict[str, Optional[str]]:
        """
        Extrae información bibliográfica de un PDF
        Estrategia híbrida:
        1. Detectar tipo de documento
        2. Artículos científicos → GROBID/regex
        3. Informes/Tesis/Libros → Claude
        4. Opcionalmente validar con Claude
        """
        doc = {}
        
        # 1. Detección rápida de tipo de documento (solo primera página)
        doc_type = self._quick_detect_document_type(pdf_content)
        logger.info(f"Tipo de documento detectado: {doc_type}")
        
        # 2. Decidir estrategia según tipo
        use_claude = False
        
        if doc_type in ['Informe técnico', 'Tesis', 'Libro', 'Capítulo de libro']:
            # Usar Claude para documentos no estándar
            logger.info(f"Documento es {doc_type}, verificando si usar Claude...")
            logger.info(f"Claude habilitado: {self.claude_extractor.use_claude}")
            logger.info(f"Claude para informes: {settings.claude_for_reports}")
            
            if (self.claude_extractor.use_claude and 
                ((doc_type == 'Informe técnico' and settings.claude_for_reports) or
                 (doc_type == 'Tesis' and settings.claude_for_thesis) or
                 (doc_type == 'Libro' and settings.claude_for_books) or
                 (doc_type == 'Capítulo de libro' and settings.claude_for_books))):
                logger.info(f"✓ Usando Claude para {doc_type}")
                try:
                    doc = self.claude_extractor.extract_from_first_pages(
                        pdf_content, 
                        num_pages=3,  # Reducido de 5 a 3 para ser más rápido
                        doc_type_hint=doc_type
                    )
                    use_claude = True
                    logger.info(f"Claude extrajo {len(doc)} campos")
                    # Si Claude funcionó, NO continuar con regex para evitar mezclar datos
                    # Solo agregar campos que Claude no extrajo pero que son seguros (como DOI del texto completo)
                    if doc:
                        logger.info("Claude extrajo datos exitosamente, usando solo esos datos")
                        # Solo complementar con DOI si no lo extrajo Claude (DOI es seguro de extraer)
                        try:
                            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                                if pdf.pages:
                                    first_page_text = pdf.pages[0].extract_text() or ""
                                    doi = extract_doi(first_page_text)
                                    if doi and not doc.get('doi'):
                                        doc['doi'] = doi
                        except:
                            pass
                        # Marcar tipo de documento si no lo hizo Claude
                        if doc_type and not doc.get('tipo_documento'):
                            doc['tipo_documento'] = doc_type
                        return doc
                except Exception as e:
                    logger.error(f"Error usando Claude, cayendo a método por defecto: {e}")
                    use_claude = False
            else:
                logger.warning(f"Claude no se usará para {doc_type} (configuración deshabilitada)")
        
        # 3. Si no se usó Claude, usar estrategia normal (GROBID + regex)
        if not use_claude:
            # Para informes, usar método específico mejorado
            if doc_type == 'Informe técnico':
                logger.info("Usando extracción mejorada para informes (sin Claude)")
                report_doc = self._extract_report_info(pdf_content, full_text=None)
                # Combinar con lo que ya se extrajo
                for key, value in report_doc.items():
                    if value and not doc.get(key):
                        doc[key] = value
                # Marcar tipo de documento
                doc['tipo_documento'] = 'Informe técnico'
            else:
                # Intentar GROBID primero (para artículos científicos)
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
                        # Validar que no sea texto de footer/metadata (validación adicional)
                        if self._validate_abstract(abstract):
                            doc['resumen_abstract'] = normalize_text(abstract)
                        else:
                            logger.warning("Abstract extraído por regex rechazado por validación")
                
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
            
            # ESTRATEGIA MEJORADA: Siempre usar Claude para complementar y corregir
            # Claude puede corregir datos incorrectos extraídos por regex
            if self.claude_extractor.use_claude:
                regex_filled = sum(1 for v in doc.values() if v is not None and v != "")
                logger.info(f"Extrayendo con regex: {regex_filled} campos llenos")
                
                # Guardar datos originales de regex para comparación
                regex_data = doc.copy()
                
                try:
                    claude_doc = self.claude_extractor.extract_from_first_pages(
                        pdf_content,
                        num_pages=3,
                        doc_type_hint=doc_type
                    )
                    
                    if claude_doc:
                        # Estrategia inteligente de combinación y corrección
                        for key, claude_value in claude_doc.items():
                            if not claude_value:  # Si Claude no tiene valor, mantener regex
                                continue
                            
                            regex_value = doc.get(key)
                            
                            # CASO 1: Campo vacío en regex → usar Claude
                            if not regex_value:
                                doc[key] = claude_value
                                logger.info(f"Claude completó campo vacío: {key} = {claude_value}")
                            
                            # CASO 2: Año - siempre validar y corregir si es necesario
                            elif key == 'ano':
                                # Extraer año del header manualmente para validar
                                header_year = self._extract_year_from_header(full_text[:2000])
                                if header_year:
                                    # Si hay año en header, usarlo (más confiable que regex o Claude)
                                    if regex_value != header_year:
                                        logger.info(f"Año corregido desde header: {header_year} (regex tenía: {regex_value}, Claude: {claude_value})")
                                    doc[key] = header_year
                                elif claude_value != regex_value:
                                    # Si no hay header, pero Claude y regex difieren, usar Claude (más confiable)
                                    logger.info(f"Año corregido por Claude: {claude_value} (regex tenía incorrecto: {regex_value})")
                                    doc[key] = claude_value
                            
                            # CASO 3: Resumen/Abstract - validar longitud y contenido
                            elif key == 'resumen_abstract':
                                MAX_ABSTRACT_LENGTH = 5000
                                
                                # Validar que no sea texto de footer/metadata
                                if isinstance(claude_value, str) and not self._validate_abstract(claude_value):
                                    logger.warning(f"Resumen de Claude rechazado por contener texto de footer/metadata")
                                    # Si regex tiene un abstract válido, mantenerlo
                                    if regex_value and self._validate_abstract(regex_value):
                                        logger.info("Manteniendo resumen de regex (Claude tenía texto inválido)")
                                        continue
                                    # Si ambos son inválidos, no usar ninguno (mejor null que texto incorrecto)
                                    logger.warning("Tanto regex como Claude extrajeron abstracts inválidos, dejando campo vacío")
                                    continue
                                
                                # Truncar si es muy largo
                                if isinstance(claude_value, str) and len(claude_value) > MAX_ABSTRACT_LENGTH:
                                    truncated = claude_value[:MAX_ABSTRACT_LENGTH]
                                    last_space = truncated.rfind(' ')
                                    if last_space > MAX_ABSTRACT_LENGTH * 0.9:
                                        truncated = truncated[:last_space]
                                    claude_value = truncated + "... [truncado]"
                                    logger.warning(f"Resumen de Claude truncado a {len(claude_value)} caracteres")
                                
                                # Validar regex también si existe
                                if regex_value and isinstance(regex_value, str) and not self._validate_abstract(regex_value):
                                    logger.warning(f"Resumen de regex rechazado por contener texto de footer/metadata")
                                    regex_value = None  # Invalidar regex
                                
                                # Usar Claude si no hay regex o si Claude es más completo
                                if not regex_value or (isinstance(claude_value, str) and isinstance(regex_value, str) and len(claude_value) > len(regex_value) * 1.1):
                                    doc[key] = claude_value
                                    logger.info(f"Resumen {'completado' if not regex_value else 'mejorado'} por Claude")
                            
                            # CASO 4: Campos críticos - permitir que Claude corrija si parece más correcto
                            elif key in ['lugar_publicacion_entrega', 'volumen_edicion', 'paginas', 'keywords', 'tipo_documento']:
                                if regex_value != claude_value:
                                    # Si Claude tiene más información o parece más completo, usarlo
                                    if isinstance(claude_value, str) and isinstance(regex_value, str):
                                        # Si Claude tiene información más completa (20% más largo), usarlo
                                        if len(claude_value) > len(regex_value) * 1.2:
                                            doc[key] = claude_value
                                            logger.info(f"Campo {key} corregido por Claude (más completo: '{claude_value}' vs '{regex_value}')")
                                        # Si regex parece más completo, mantenerlo
                                        elif len(regex_value) > len(claude_value) * 1.2:
                                            logger.debug(f"Manteniendo {key} de regex (más completo que Claude)")
                                        # Si son similares pero diferentes, usar Claude si regex está vacío o parece incorrecto
                                        elif not regex_value or len(regex_value) < 3:
                                            doc[key] = claude_value
                                            logger.info(f"Campo {key} corregido por Claude (regex parece incorrecto: '{regex_value}')")
                            
                            # CASO 5: Otros campos - solo completar si está vacío
                            elif not regex_value:
                                doc[key] = claude_value
                                logger.info(f"Claude completó campo: {key}")
                        
                        claude_filled = sum(1 for v in doc.values() if v is not None and v != "")
                        logger.info(f"Después de Claude: {claude_filled} campos llenos (regex tenía: {regex_filled})")
                
                except Exception as e:
                    logger.warning(f"Error usando Claude para complementar/corregir: {e}")
                    # Continuar con datos de regex si Claude falla
            
            # Opcionalmente validar con Claude (solo si está habilitado y no se usó arriba)
            elif (settings.claude_as_validator and 
                self.claude_extractor.use_claude and
                doc.get('titulo_original')):  # Solo si hay datos para validar
                logger.info("Validando con Claude")
                doc = self.claude_extractor.validate_and_enrich(
                    doc, 
                    pdf_content, 
                    num_pages=3
                )
                
        except Exception as e:
            logger.error(f"Error extracting PDF: {e}")
        
        return doc
    
    def _extract_year_from_header(self, text: str) -> Optional[int]:
        """Extrae año específicamente del header de revista (más confiable)"""
        # Buscar formato: "Journal, Location, Volume: Pages, Year"
        # Ejemplo: "Invest. Mar., Valparaíso, 28: 39-52, 2000"
        header_patterns = [
            r':\s*\d+[-\u2013\u2014]\d+,\s*(\d{4})',  # "28: 39-52, 2000"
            r',\s*(\d{4})\s*$',  # Año al final de línea
        ]
        
        for pattern in header_patterns:
            matches = list(re.finditer(pattern, text, re.MULTILINE))
            if matches:
                try:
                    match = matches[-1]  # Tomar el último (más probable)
                    year = int(match.group(1))
                    if 1900 <= year <= 2100:
                        from datetime import datetime
                        current_year = datetime.now().year
                        if year <= current_year + 2:
                            return year
                except (ValueError, IndexError):
                    pass
        return None
    
    def _quick_detect_document_type(self, pdf_content: bytes) -> Optional[str]:
        """Detección rápida de tipo de documento (solo primera página)"""
        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                if pdf.pages:
                    first_page_text = pdf.pages[0].extract_text() or ""
                    first_page_lower = first_page_text.lower()
                    
                    # Patrones de detección (mejorados)
                    # Informes: buscar "INFORME" en mayúsculas o cualquier variante
                    if (re.search(r'\b(?:informe\s+final|informe\s+técnico|technical\s+report|report\s+final)', first_page_lower) or
                        re.search(r'INFORME\s+FINAL', first_page_text) or
                        re.search(r'INFORME\s+TÉCNICO', first_page_text)):
                        logger.info("Documento detectado como: Informe técnico")
                        return 'Informe técnico'
                    if re.search(r'\b(?:tesis|thesis|dissertation|doctoral|ph\.?d\.?)', first_page_lower):
                        logger.info("Documento detectado como: Tesis")
                        return 'Tesis'
                    if re.search(r'\b(?:libro|book|editorial|publisher)', first_page_lower):
                        if re.search(r'\bIn:\s*', first_page_text, re.IGNORECASE):
                            logger.info("Documento detectado como: Capítulo de libro")
                            return 'Capítulo de libro'
                        logger.info("Documento detectado como: Libro")
                        return 'Libro'
                    if re.search(r'\b(?:journal|revista|article|vol\.|volume)', first_page_lower):
                        logger.info("Documento detectado como: Artículo en revista científica")
                        return 'Artículo en revista científica'
        except Exception as e:
            logger.warning(f"Error detectando tipo de documento: {e}")
        
        logger.info("Tipo de documento no detectado, usando método por defecto")
        return None
    
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
                if re.match(BiblioPatterns.YEAR_SHORT, line):
                    continue
                
                # No debe contener email
                if '@' in line:
                    continue
                
                # No debe ser "doi:" o similar
                if 'doi:' in line.lower() and len(line) < 50:
                    continue
                
                # No debe empezar con "Author", "Abstract", etc.
                if ExtractionPatterns.is_excluded_title(line):
                    continue
                
                # Si la línea es significativamente larga y parece título, agregarla como candidato
                if len(line) > 30:
                    # Intentar agregar espacios entre palabras que están juntas
                    if re.search(ValidationPatterns.HAS_CONCAT_WORDS, line):
                        line = TextNormalizer.normalize_spacing(line)
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
                        not re.match(BiblioPatterns.AUTHOR_FULL, next_line) and
                        not re.match(BiblioPatterns.YEAR_SHORT, next_line) and
                        '@' not in next_line and
                        'doi:' not in next_line.lower() and
                        not ExtractionPatterns.is_excluded_title(next_line)):
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
        
        # Buscar sección de autores común (mejorado)
        # Incluye múltiples variantes: Author, Autores, Equipo de Trabajo, Investigador Responsable, etc.
        author_sections = [
            r'Author[s]?[:\s]+(.+?)(?:\n\n|\nAbstract|\nSummary|\nKeywords|^Abstract|^Summary|\nResumen)',
            r'Autores?[:\s]+(.+?)(?:\n\n|\nAbstract|\nSummary|\nKeywords|^Abstract|^Summary|\nResumen)',
            r'Equipo\s+de\s+Trabajo[:\s]+(.+?)(?:\n\n|\nAbstract|\nSummary|\nKeywords|^Abstract|^Summary|\nResumen|\nIntroducción)',
            r'Equipo[:\s]+(.+?)(?:\n\n|\nAbstract|\nSummary|\nKeywords|^Abstract|^Summary|\nResumen|\nIntroducción)',
            r'Investigador\s+Responsable[:\s]+(.+?)(?:\n\n|\nAbstract|\nSummary|\nKeywords|^Abstract|^Summary|\nResumen|\nIntroducción)',
            r'Investigador[:\s]+(.+?)(?:\n\n|\nAbstract|\nSummary|\nKeywords|^Abstract|^Summary|\nResumen|\nIntroducción)',
            r'Responsable[:\s]+(.+?)(?:\n\n|\nAbstract|\nSummary|\nKeywords|^Abstract|^Summary|\nResumen|\nIntroducción)',
            r'Coordinador[:\s]+(.+?)(?:\n\n|\nAbstract|\nSummary|\nKeywords|^Abstract|^Summary|\nResumen|\nIntroducción)',
            r'Director[:\s]+(.+?)(?:\n\n|\nAbstract|\nSummary|\nKeywords|^Abstract|^Summary|\nResumen|\nIntroducción)',
        ]
        
        for pattern in author_sections:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                authors = match.group(1).strip()
                
                # Si el match capturó hasta el final del documento, limitar a las primeras líneas
                # (normalmente los autores están en 1-5 líneas después del encabezado)
                author_lines = authors.split('\n')[:10]  # Máximo 10 líneas
                authors = '\n'.join(author_lines)
                
                # Validar que no contenga patrones excluidos
                should_exclude = False
                for exclude_pattern in exclude_patterns:
                    if re.search(exclude_pattern, authors, re.IGNORECASE):
                        should_exclude = True
                        break
                
                if should_exclude:
                    continue
                
                # Limpiar y validar
                authors = TextNormalizer.clean_multiple_spaces(authors)
                # Reemplazar saltos de línea con comas para unificar formato
                authors = re.sub(r'\n+', ', ', authors)
                authors = TextNormalizer.clean_multiple_spaces(authors)
                
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
                    re.match(BiblioPatterns.YEAR_SHORT, line) or
                    ExtractionPatterns.is_excluded_title(line)):
                    continue
                
                # Patrón de autor mejorado: múltiples formatos
                # Ejemplos:
                # - "Porobic, J., Fulton, E.A., Parada, C."
                # - "Ernst, B., Oyarzun, C., Vilches, J."
                # - "Apellido Inicial" (sin coma ni punto)
                # - "Apellido, Inicial" (sin punto)
                # - Múltiples líneas de autores
                author_patterns = [
                    r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?,\s*[A-Z]\.',     # "Apellido, Inicial."
                    r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?,\s*[A-Z]',        # "Apellido, Inicial" (sin punto)
                    r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-Z]\.',                                      # "Apellido Inicial." (sin coma)
                    r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-Z](?:\s|,|$)',                              # "Apellido Inicial" (sin coma ni punto)
                    r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+,\s*[A-Z]\.?\s*,\s*[A-Z]',                        # Múltiples autores separados por coma
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
                authors = TextNormalizer.clean_multiple_spaces(authors)
                # Limpiar comas y puntos finales
                authors = authors.rstrip(',. ')
                return normalize_text(authors)
        
        return None
    
    def _validate_abstract(self, abstract: str) -> bool:
        """Valida que el abstract no sea texto de footer/metadata"""
        if not abstract or len(abstract.strip()) < 10:
            return False
        
        # Patrones que indican que es texto de footer/metadata (no abstract real)
        exclude_patterns = [
            r'www\.\w+\.(org|com|edu|net|mx)',  # URLs
            r'http[s]?://',  # URLs completas
            r'Proyecto académico',  # Metadata de sitios
            r'sin fines de lucro',  # Metadata
            r'desarrollado bajo',  # Metadata
            r'redalyc',  # Nombre de sitio
            r'ArtPdfRed',  # Metadata de redalyc
            r'\.(org|com|edu|net|mx)\s',  # Dominios en el texto
            r'^[A-Z][a-z]+\s+www\.',  # "Chile www..." (patrón común en footers)
        ]
        
        abstract_lower = abstract.lower()
        
        # Verificar si contiene patrones de exclusión
        for pattern in exclude_patterns:
            if re.search(pattern, abstract, re.IGNORECASE):
                logger.warning(f"Abstract rechazado por contener texto de footer/metadata: {pattern}")
                return False
        
        # Validar que tenga contenido sustancial
        # Un abstract real debe tener varias palabras y no ser solo URLs/metadata
        words = abstract.split()
        if len(words) < 10:  # Muy corto, probablemente no es abstract
            return False
        
        # Si más del 30% del texto son URLs o dominios, probablemente no es abstract
        url_like_chars = sum(1 for word in words if '.' in word and len(word) < 20)
        if url_like_chars > len(words) * 0.3:
            logger.warning("Abstract rechazado: demasiadas palabras que parecen URLs")
            return False
        
        return True
    
    def _extract_abstract(self, text: str) -> Optional[str]:
        """Extrae abstract o resumen con límites de longitud y validación"""
        # Buscar sección de abstract con delimitadores más estrictos
        patterns = [
            r'Abstract[:\s]+(.+?)(?:\n\n|\nKeywords|\nIntroduction|\nResumen|\n1\.\s|^Keywords|^Introduction)',
            r'Resumen[:\s]+(.+?)(?:\n\n|\nPalabras|\nIntroducción|\n1\.\s|^Palabras|^Introducción)',
            r'SUMMARY[:\s]+(.+?)(?:\n\n|\nKeywords|\nIntroduction|\n1\.\s|^Keywords|^Introduction)',
        ]
        
        MAX_ABSTRACT_LENGTH = 5000  # Máximo 5000 caracteres (~800 palabras)
        MIN_ABSTRACT_LENGTH = 50
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
            if match:
                abstract = match.group(1).strip()
                
                # Limpiar espacios múltiples
                abstract = TextNormalizer.clean_multiple_spaces(abstract)
                
                # Validar que no sea texto de footer/metadata
                if not self._validate_abstract(abstract):
                    continue  # Intentar siguiente patrón
                
                # Truncar si es muy largo (cortar en palabra completa)
                if len(abstract) > MAX_ABSTRACT_LENGTH:
                    abstract = abstract[:MAX_ABSTRACT_LENGTH]
                    # Buscar último espacio para no cortar en medio de palabra
                    last_space = abstract.rfind(' ')
                    if last_space > MAX_ABSTRACT_LENGTH * 0.9:  # Si el último espacio está cerca del límite
                        abstract = abstract[:last_space]
                    abstract += "... [truncado]"
                
                # Validar longitud mínima y máxima
                if MIN_ABSTRACT_LENGTH < len(abstract) <= MAX_ABSTRACT_LENGTH + 20:  # +20 para el texto "[truncado]"
                    return normalize_text(abstract)
        
        return None
    
    def _extract_keywords(self, text: str) -> Optional[str]:
        """Extrae keywords o palabras clave - Mejorado"""
        # Buscar al final del abstract también
        patterns = [
            r'Keywords?[:\s]+(.+?)(?:\n\n|Abstract|Introduction|1\.|$)',
            r'Palabras\s+clave[:\s]+(.+?)(?:\n\n|Resumen|Introducción|1\.|$)',
            r'Palabras\s+claves?[:\s]+(.+?)(?:\n\n|Resumen|Introducción|1\.|$)',
            # Buscar al final del abstract (patrón común en español)
            # Ejemplo: "...islas analizadas. Palabras claves: pesca exploratoria, trampas, crustáceos, archipiélago de Juan Fernández, Chile."
            r'(?:\.|;)\s*(?:Palabras\s+claves?|Keywords?)[:\s]+(.+?)(?:\.|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
            if match:
                keywords = match.group(1).strip()
                # Limpiar saltos de línea y caracteres especiales al final
                keywords = keywords.rstrip('.,;')
                keywords = TextNormalizer.clean_multiple_spaces(keywords)
                
                # Si las keywords están separadas por comas, agregar espacio después de cada coma
                if ',' in keywords:
                    keywords = re.sub(r',\s*', ', ', keywords)
                
                if 5 < len(keywords) < 500:
                    return keywords
        
        return None
    
    def _extract_journal(self, text: str) -> Optional[str]:
        """Extrae nombre de revista - Mejorado para detectar headers"""
        # PRIMERO: Buscar formato de header común: "Journal, Location, Volume: Pages, Year"
        # Ejemplo: "Invest. Mar., Valparaíso, 28: 39-52, 2000"
        first_part = text[:2000]  # Solo primeras 2000 caracteres (donde suele estar el header)
        header_patterns = [
            r'^([A-Z][a-zA-ZáéíóúÁÉÍÓÚÑñ\s\.]+?),\s*([A-Z][a-zA-ZáéíóúÁÉÍÓÚÑñ\s]+?),\s*\d+:\s*\d+[-\u2013\u2014]\d+,\s*\d{4}',
            r'^([A-Z][a-zA-ZáéíóúÁÉÍÓÚÑñ\s\.]+?)\s*,\s*([A-Z][a-zA-ZáéíóúÁÉÍÓÚÑñ\s]+?)\s*,\s*\d+:',  # Sin año al final
        ]
        
        for pattern in header_patterns:
            matches = list(re.finditer(pattern, first_part, re.MULTILINE))
            if matches:
                match = matches[0]  # Tomar el primero (más arriba)
                journal = match.group(1).strip()
                if len(match.groups()) > 1:
                    location = match.group(2).strip()
                    # Validar que no sea demasiado largo (probablemente no es journal)
                    if len(journal) < 100 and len(location) < 100:
                        result = f"{journal}, {location}"
                        logger.info(f"Revista extraída del header: {result}")
                        return normalize_text(result)
        
        # SEGUNDO: Buscar patrones tradicionales
        patterns = [
            r'Published\s+in[:\s]+(.+?)(?:\n|,|\.)',
            r'Journal\s+of[:\s]+(.+?)(?:\n|,|\.)',
            r'Revista[:\s]+(.+?)(?:\n|,|\.)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return normalize_text(match.group(1))
        
        return None
    
    def _extract_pages(self, text: str) -> Optional[str]:
        """Extrae páginas - Mejorado para detectar headers"""
        # PRIMERO: Buscar en formato de header: "Volume: Pages, Year"
        # Ejemplo: "28: 39-52, 2000"
        first_part = text[:2000]  # Solo primeras 2000 caracteres
        header_pages_patterns = [
            r'\d+:\s*(\d+[-\u2013\u2014]\d+),\s*\d{4}',  # "28: 39-52, 2000"
            r'pp\.?\s*(\d+[-\u2013\u2014]\d+)',  # "pp. 39-52"
            r'p\.?\s*(\d+[-\u2013\u2014]\d+)',  # "p. 39-52"
        ]
        
        for pattern in header_pages_patterns:
            match = re.search(pattern, first_part, re.MULTILINE)
            if match:
                pages = match.group(1)
                logger.info(f"Páginas extraídas del header: {pages}")
                return pages
        
        # SEGUNDO: Buscar patrones tradicionales
        pattern = r'Pages?[:\s]+(\d+[-\u2013\u2014]\d+|\d+)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_volume(self, text: str) -> Optional[str]:
        """Extrae volumen - Mejorado para detectar headers"""
        # PRIMERO: Buscar en formato de header: "Volume: Pages, Year"
        # Ejemplo: "28: 39-52, 2000"
        first_part = text[:2000]  # Solo primeras 2000 caracteres
        header_volume_patterns = [
            r'(\d+):\s*\d+[-\u2013\u2014]\d+,\s*\d{4}',  # "28: 39-52, 2000"
            r'Vol\.?\s*(\d+)',  # "Vol. 28"
        ]
        
        for pattern in header_volume_patterns:
            match = re.search(pattern, first_part, re.MULTILINE)
            if match:
                volume = match.group(1)
                logger.info(f"Volumen extraído del header: {volume}")
                return volume
        
        # SEGUNDO: Buscar patrones tradicionales
        patterns = [
            r'Volume[:\s]+(\d+)',
            r'Volumen[:\s]+(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

