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
    def clean_references_header(text: str) -> str:
        """Limpia el header 'REFERENCES' del inicio del texto"""
        return re.sub(r'^(REFERENCES|References)\s+', '', text, flags=re.IGNORECASE).strip()
    
    @staticmethod
    def clean_multiple_spaces(text: str) -> str:
        """Limpia espacios múltiples"""
        return re.sub(r'\s+', ' ', text).strip()

