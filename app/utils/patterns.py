"""
Módulo centralizado de patrones regex para extracción bibliográfica.
Evita duplicación de código y facilita mantenimiento.
"""
import re
from typing import List, Pattern


class BiblioPatterns:
    """Patrones regex reutilizables para extracción bibliográfica"""
    
    # ========== PATRONES DE AUTORES ==========
    # Patrón básico: Apellido, Inicial.
    AUTHOR_BASIC = r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?'
    
    # Patrón completo: Apellido, Inicial., Apellido, Inicial.
    AUTHOR_FULL = rf'^{AUTHOR_BASIC},\s*[A-Z]\.?'
    
    # Patrón con año: Apellido, Inicial. (año) o Apellido, Inicial., año
    AUTHOR_WITH_YEAR = rf'^{AUTHOR_BASIC}[\s,]*\(?\d{{4}}'
    
    # Patrón de autor completo con múltiples autores
    AUTHOR_MULTIPLE = rf'^({AUTHOR_BASIC}(?:,\s*[A-Z]\.?)+,?\s*)+'
    
    # Validación: tiene al menos un autor completo
    AUTHOR_VALID = r'[A-Z][a-z]+,\s*[A-Z]\.'
    
    # Patrón para buscar autor en cualquier parte del texto (no solo inicio)
    # Formato: "Apellido, Inicial." - usado para detectar inicio de referencia
    AUTHOR_SEARCH = r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,},\s*[A-Z]\.'
    
    # Patrón para autor con inicial después de coma (validación)
    AUTHOR_COMMA_INITIAL = r',\s*[A-Z]\.'
    
    # Patrón para autor sin coma (formato alternativo)
    AUTHOR_NO_COMMA = r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}\s+[A-Z]\.'
    
    # Patrón para excluir casos como "America, 1967-73" (solo apellido y año con guión)
    AUTHOR_YEAR_RANGE_EXCLUDE = r'[A-Z][a-z]+,\s*\d{4}[-–—]'
    
    # Patrón para múltiples autores separados por coma
    AUTHOR_MULTIPLE_COMMA = r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,},\s*[A-Z]\.?\s*,\s*[A-Z]'
    
    # ========== PATRONES DE AÑOS ==========
    # Año de 4 dígitos (1900-2099)
    YEAR_FULL = r'\b(19\d{2}|20[0-2]\d)\b'
    
    # Año corto (19xx o 20xx)
    YEAR_SHORT = r'\b(19|20)\d{2}\b'
    
    # ========== PATRONES DE DOI ==========
    # DOI en URL
    DOI_URL = r'https?://(?:dx\.)?doi\.org/(10\.\d{4,}/[^\s\)]+)'
    
    # DOI con etiqueta
    DOI_LABEL = r'doi[:\s]+(10\.\d{4,}/[^\s\)]+)'
    
    # DOI directo
    DOI_DIRECT = r'(10\.\d{4,}/[a-zA-Z0-9\.\-]+)'
    
    # Validación DOI
    DOI_VALID = r'10\.\d{4,}/.+'
    
    # ========== PATRONES DE TÍTULOS ==========
    # Título entre comillas
    TITLE_QUOTED = r'["\'](.+?)["\']'
    
    # Título después de año (formato estándar)
    TITLE_AFTER_YEAR = r'\.\s+([A-Z][^\.]+?)(?:\.\s+[A-Z][a-z]*\.|\.\s+In:|\.\s+pp\.)'
    
    # ========== PATRONES DE REFERENCIAS ==========
    # Inicio de sección de referencias
    REF_SECTION_START = r'^(REFERENCES|References|REFERENCIAS|Bibliografía|Bibliography|LITERATURE\s+CITED|Works\s+Cited)'
    
    # Referencia numerada
    REF_NUMBERED = r'^\d+\.\s+[A-Z]'
    
    # ========== PATRONES DE EXCLUSIÓN (Headers/Footers) ==========
    # Headers comunes
    HEADER_FRONTIERS = r'^Frontiers'
    HEADER_VOLUME = r'^Volume \d+'
    HEADER_ARTICLE = r'^Article \d+'
    HEADER_DOI = r'^doi:'
    HEADER_HTTP = r'^http'
    HEADER_WWW = r'^www\.'
    
    # Secciones no relevantes
    SECTION_FUNDING = r'^(FUNDING|Funding)'
    SECTION_ACKNOWLEDGMENTS = r'^(ACKNOWLEDGMENTS?|Acknowledgments?)'
    SECTION_DATA_AVAILABILITY = r'^(DATA AVAILABILITY|Data Availability)'
    SECTION_SUPPLEMENTARY = r'^(SUPPLEMENTARY|Supplementary)'
    SECTION_AUTHOR_CONTRIBUTIONS = r'^(AUTHOR CONTRIBUTIONS|Author Contributions)'
    
    # Frases inválidas en referencias
    INVALID_PHRASES = [
        'THIS RESEARCH WAS SPONSORED',
        'FONDAP-CONICYT',
        'FONDEQUIP',
        'FONDECYT',
        'WE APPRECIATE',
        'THE ORIGINAL CONTRIBUTIONS',
        'FURTHER INQUIRIES',
        'SUPPLEMENTARY MATERIAL',
        'AUTHOR CONTRIBUTIONS',
        'ENDORSED BY THE PUBLISHER',
        'NO USE, DISTRIBUTION OR REPRODUCTION',
    ]
    
    @classmethod
    def get_header_patterns(cls) -> List[str]:
        """Retorna lista de patrones de headers a excluir"""
        return [
            cls.HEADER_FRONTIERS,
            cls.HEADER_VOLUME,
            cls.HEADER_ARTICLE,
            cls.HEADER_DOI,
            cls.HEADER_HTTP,
            cls.HEADER_WWW,
        ]
    
    @classmethod
    def get_section_patterns(cls) -> List[str]:
        """Retorna lista de patrones de secciones a excluir"""
        return [
            cls.SECTION_FUNDING,
            cls.SECTION_ACKNOWLEDGMENTS,
            cls.SECTION_DATA_AVAILABILITY,
            cls.SECTION_SUPPLEMENTARY,
            cls.SECTION_AUTHOR_CONTRIBUTIONS,
        ]
    
    @classmethod
    def is_header(cls, text: str) -> bool:
        """Verifica si un texto es un header/footer"""
        for pattern in cls.get_header_patterns():
            if re.match(pattern, text, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def is_section(cls, text: str) -> bool:
        """Verifica si un texto es una sección no relevante"""
        for pattern in cls.get_section_patterns():
            if re.match(pattern, text, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def is_reference_section(cls, text: str) -> bool:
        """Verifica si un texto es inicio de sección de referencias"""
        return bool(re.match(cls.REF_SECTION_START, text, re.IGNORECASE))
    
    @classmethod
    def contains_invalid_phrase(cls, text: str) -> bool:
        """Verifica si un texto contiene frases inválidas"""
        text_upper = text.upper()
        return any(phrase in text_upper for phrase in cls.INVALID_PHRASES)


class CleaningPatterns:
    """Patrones para limpieza de texto"""
    
    # ========== PATRONES DE NORMALIZACIÓN ==========
    # Normalizar espacios después de comas en nombres: "Apellido,Inicial" -> "Apellido, Inicial"
    NORMALIZE_AUTHOR_COMMA = r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}),([A-ZÁÉÍÓÚÑ])'
    NORMALIZE_AUTHOR_COMMA_REPL = r'\1, \2'
    
    # Normalizar espacios entre autores: "autor,Apellido" -> "autor, Apellido"
    NORMALIZE_AUTHOR_LIST = r'([a-záéíóúñ]),([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})'
    NORMALIZE_AUTHOR_LIST_REPL = r'\1, \2'
    
    # Normalizar espacios después de iniciales: "J.Mar." -> "J. Mar."
    NORMALIZE_INITIALS = r'([A-Z])\.([A-Z])'
    NORMALIZE_INITIALS_REPL = r'\1. \2'
    
    # Normalizar palabras concatenadas: "Highfrequency" -> "High frequency"
    NORMALIZE_CONCAT_WORDS = r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,})'
    NORMALIZE_CONCAT_WORDS_REPL = r'\1 \2'
    
    # ========== PATRONES DE LIMPIEZA DE HEADERS/FOOTERS ==========
    CLEAN_FRONTIERS = r'Frontiers in Marine Science.*?(?=\n|$)'
    CLEAN_VOLUME = r'Volume \d+.*?(?=\n|$)'
    CLEAN_ARTICLE = r'Article \d+.*?(?=\n|$)'
    CLEAN_WWW = r'www\.frontiersin\.org.*?(?=\n|$)'
    
    # ========== PATRONES DE LIMPIEZA DE SALTOS DE LÍNEA ==========
    CLEAN_CRLF = r'\r\n'
    CLEAN_CR = r'\r'
    CLEAN_MULTIPLE_SPACES = r'\s+'
    
    # ========== PATRONES DE TEXTO BASURA AL INICIO ==========
    GARBAGE_PATTERNS = [
        r'^and\s+approved\s+the\s+submitted\s+version\.?\s*',
        r'^submitted\s+version\.?\s*',
        r'^approved\s+the\s+submitted\.?\s*',
        r'^and\s+approved\.?\s*',
        r'^REFERENCES\s+',
        r'^References\s+',
        r'^\.\s*',  # Punto al inicio
        r'^,\s*',   # Coma al inicio
    ]
    
    @classmethod
    def clean_garbage_patterns(cls, text: str) -> str:
        """Elimina patrones de texto basura al inicio"""
        for pattern in cls.GARBAGE_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
        return text


class SplitPatterns:
    """Patrones para dividir referencias"""
    
    # Patrón para detectar inicio de referencia en texto consolidado
    # Formato: final de referencia anterior + inicio de nueva
    REF_START_FULL = r'(?:^|\.\s|\)\.?\s|doi:[^\s]+\s|[\d]+–[\d]+\.?\s)([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,},\s*[A-Z]\.)'
    
    # Patrón simplificado para inicio de referencia
    REF_START_SIMPLE = r'(?:^|\.doi:[^\s]+\s+|[\d]+–[\d]+\.\s+|[\d]{4}\)\.\s*)([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,},\s*[A-Z]\.)'
    
    # Patrón para dividir por años: (2009) o 2009.
    REF_SPLIT_YEAR = r'(\(\d{4}\)|\s\d{4}[\.,])'


class ValidationPatterns:
    """Patrones para validación"""
    
    # Validar que no es solo números
    ONLY_NUMBERS = r'^\d+$'
    
    # Validar que no es solo mayúsculas cortas (metadata)
    ONLY_UPPERCASE_SHORT = r'^[A-Z\s]{1,30}$'
    
    # Validar que tiene minúscula seguida de mayúscula (palabras concatenadas)
    HAS_CONCAT_WORDS = r'[a-z][A-Z]'


class ExtractionPatterns:
    """Patrones para extracción de campos específicos"""
    
    # ========== PATRONES DE EXCLUSIÓN PARA TÍTULOS ==========
    EXCLUDE_METADATA = [
        r'^Author',
        r'^Abstract',
        r'^Summary',
        r'^Keywords',
        r'^Received',
        r'^Accepted',
        r'^Published',
        r'^Editor',
        r'^Citation',
        r'^RESEARCH ARTICLE',
        r'^REVIEW ARTICLE',
    ]
    
    # ========== PATRONES DE AUTORES ==========
    # Formato estándar: "Apellido, Inicial." con posibles espacios
    AUTHOR_PATTERN = r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?,\s*[A-Z]\.(?:\s*[A-Z]\.)*)'
    
    # Formato sin coma: "Apellido Inicial" (común en algunas referencias)
    AUTHOR_PATTERN_NO_COMMA = r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?\s+[A-Z](?:\s*[A-Z])?)'
    
    # Secciones donde buscar autores
    AUTHOR_SECTIONS = [
        r'(?:By|Authors?|Written by)[:\s]+(.+?)(?=\n\n|\n[A-Z][a-z]+:)',
        r'^(.+?)\n+Abstract',
    ]
    
    # ========== PATRONES DE AÑO ==========
    # Año entre paréntesis (más confiable)
    YEAR_PARENTHESIS = r'\((\d{4})\)'
    
    # Año seguido de punto y espacio
    YEAR_DOT_SPACE = r'(\d{4})\.\s+[A-Z]'
    
    # Año seguido de punto
    YEAR_DOT = r'(\d{4})\.'
    
    # Año seguido de punto y coma (común en referencias con volumen)
    YEAR_SEMICOLON = r'(\d{4});'
    
    # Año seguido de coma (otro formato común)
    YEAR_COMMA = r'(\d{4}),'
    
    # ========== PATRONES DE TÍTULO ==========
    # Buscar fin de título: punto seguido de abreviación de revista
    TITLE_END_JOURNAL = r'\.\s+([A-Z][\w\s\.\,&-]{1,50}?)\s+\d+'
    
    # Buscar primer punto (fallback)
    TITLE_END_DOT = r'\.\s'
    
    # ========== PATRONES DE REVISTA ==========
    # Formato: "J. Mar. Syst. 78" o "Marine Ecology 123"
    JOURNAL_VOLUME = r'\.\s+([A-Z][\w\s\.\,&-]{1,50}?)\s+(\d+)'
    
    # ========== PATRONES DE PÁGINAS ==========
    PAGES_PATTERN = r'Pages?[:\s]+(\d+[-\u2013\u2014]\d+|\d+)'
    
    # ========== PATRONES DE VOLUMEN ==========
    VOLUME_PATTERN = r'Volume[:\s]+(\d+)'
    
    # ========== PATRONES DE URL ==========
    URL_PATTERN = r'https?://[^\s\)]+'
    
    # ========== PATRONES DE LIBRO (Capítulos) ==========
    # Detectar "In:" para capítulos de libro
    IN_BOOK = r'\bIn:\s*'
    
    # Detectar editores
    EDITORS = r'\(Eds?\.\)'
    
    # Patrones de fin de título de libro
    BOOK_TITLE_END = [
        r'\bpp\.',
        r'\.\s+[A-Z][a-z]+\s+\d{4}',
        r'\.\s+\d{1,4}\s*$',
    ]
    
    # ========== PATRONES DE KEYWORDS ==========
    KEYWORDS_PATTERNS = [
        r'Keywords[:\s]+(.+?)(?=\n\n|Abstract|Introduction|\Z)',
        r'Key\s+words[:\s]+(.+?)(?=\n\n|Abstract|Introduction|\Z)',
    ]
    
    # ========== PATRONES DE ABSTRACT ==========
    ABSTRACT_PATTERNS = [
        r'Abstract[:\s]+(.+?)(?=\n\n|Keywords|Introduction|\Z)',
        r'Summary[:\s]+(.+?)(?=\n\n|Keywords|Introduction|\Z)',
    ]
    
    @classmethod
    def is_excluded_title(cls, line: str) -> bool:
        """Verifica si una línea debe excluirse de títulos"""
        for pattern in cls.EXCLUDE_METADATA:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False


class TextNormalizer:
    """Utilidades para normalización de texto"""
    
    @staticmethod
    def normalize_spacing(text: str) -> str:
        """
        Normaliza espacios en texto agregando espacios entre palabras concatenadas.
        Útil para texto extraído de PDFs que puede tener palabras sin espacios.
        """
        # Agregar espacio después de minúscula seguida de mayúscula
        text = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', text)
        # Agregar espacio después de número seguido de letra
        text = re.sub(r'(\d)([A-ZÁÉÍÓÚÑa-záéíóúñ])', r'\1 \2', text)
        # Agregar espacio antes de número seguido de letra (si no hay espacio)
        text = re.sub(r'([A-ZÁÉÍÓÚÑa-záéíóúñ])(\d)', r'\1 \2', text)
        return text
    
    @staticmethod
    def normalize_text_spacing(text: str) -> str:
        """
        Normalización completa de espaciado en texto.
        Incluye todas las normalizaciones de autores, iniciales y palabras concatenadas.
        """
        # Normalizar espacios entre palabras concatenadas primero
        text = TextNormalizer.normalize_spacing(text)
        
        # Normalizar espacios después de comas en autores
        text = re.sub(CleaningPatterns.NORMALIZE_AUTHOR_COMMA, 
                     CleaningPatterns.NORMALIZE_AUTHOR_COMMA_REPL, text)
        
        # Normalizar espacios en listas de autores
        text = re.sub(CleaningPatterns.NORMALIZE_AUTHOR_LIST,
                     CleaningPatterns.NORMALIZE_AUTHOR_LIST_REPL, text)
        
        # Normalizar espacios después de iniciales
        text = re.sub(CleaningPatterns.NORMALIZE_INITIALS,
                     CleaningPatterns.NORMALIZE_INITIALS_REPL, text)
        
        # Normalizar palabras concatenadas largas
        text = re.sub(CleaningPatterns.NORMALIZE_CONCAT_WORDS,
                     CleaningPatterns.NORMALIZE_CONCAT_WORDS_REPL, text)
        
        # Limpiar espacios múltiples
        text = re.sub(CleaningPatterns.CLEAN_MULTIPLE_SPACES, ' ', text).strip()
        
        return text
    
    @staticmethod
    def clean_line_breaks(text: str) -> str:
        """Normaliza todos los tipos de saltos de línea a \n"""
        text = re.sub(CleaningPatterns.CLEAN_CRLF, '\n', text)
        text = re.sub(CleaningPatterns.CLEAN_CR, '\n', text)
        return text
    
    @staticmethod
    def clean_headers_footers(text: str) -> str:
        """Elimina headers y footers comunes de PDFs"""
        text = re.sub(CleaningPatterns.CLEAN_FRONTIERS, '', text, flags=re.IGNORECASE)
        text = re.sub(CleaningPatterns.CLEAN_VOLUME, '', text, flags=re.IGNORECASE)
        text = re.sub(CleaningPatterns.CLEAN_ARTICLE, '', text, flags=re.IGNORECASE)
        text = re.sub(CleaningPatterns.CLEAN_WWW, '', text, flags=re.IGNORECASE)
        return text
    
    @staticmethod
    def clean_references_header(text: str) -> str:
        """Limpia el header 'REFERENCES' del inicio del texto"""
        return re.sub(r'^(REFERENCES|References)\s+', '', text, flags=re.IGNORECASE).strip()
    
    @staticmethod
    def clean_multiple_spaces(text: str) -> str:
        """Limpia espacios múltiples"""
        return re.sub(CleaningPatterns.CLEAN_MULTIPLE_SPACES, ' ', text).strip()

