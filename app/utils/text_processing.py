import re
from typing import Optional, List


def extract_doi(text: str) -> Optional[str]:
    """Extrae DOI de un texto"""
    # Patrón común para DOI: 10.xxxx/xxxx
    doi_pattern = r'10\.\d{4,}/[^\s\)]+'
    match = re.search(doi_pattern, text)
    if match:
        doi = match.group(0)
        # Limpiar caracteres finales comunes
        doi = doi.rstrip('.,;:')
        return doi
    return None


def extract_year(text: str) -> Optional[int]:
    """Extrae año de publicación (generalmente 4 dígitos entre 1900-2100)"""
    # Buscar años completos de 4 dígitos
    year_pattern = r'\b(19\d{2}|20\d{2})\b'
    matches = re.findall(year_pattern, text)
    if matches:
        # Tomar el último año encontrado (más probable que sea el año de publicación)
        try:
            # Convertir a int y validar rango razonable
            year = int(matches[-1])
            if 1900 <= year <= 2100:
                return year
        except (ValueError, IndexError):
            pass
    return None


def extract_isbn_issn(text: str) -> Optional[str]:
    """Extrae ISBN o ISSN de un texto"""
    # Patrón para ISBN-13 o ISBN-10
    isbn_pattern = r'ISBN[-\s]?(?:13[-\s]?:?)?[-\s]?(\d{13}|\d{10})|ISBN[-\s]?(\d{10})'
    # Patrón para ISSN
    issn_pattern = r'ISSN[-\s]?(\d{4}[-\s]?\d{3}[\dX])'
    
    isbn_match = re.search(isbn_pattern, text, re.IGNORECASE)
    if isbn_match:
        return isbn_match.group(1) or isbn_match.group(2)
    
    issn_match = re.search(issn_pattern, text, re.IGNORECASE)
    if issn_match:
        return issn_match.group(1).replace(' ', '').replace('-', '')
    
    return None


def normalize_text(text: Optional[str]) -> Optional[str]:
    """Normaliza texto eliminando espacios extra y caracteres especiales"""
    if not text:
        return None
    # Eliminar espacios múltiples y saltos de línea
    text = re.sub(r'\s+', ' ', text)
    return text.strip() or None


def format_authors(authors: List[dict]) -> Optional[str]:
    """Formatea lista de autores en formato: Apellido, Inicial., Apellido, Inicial."""
    if not authors:
        return None
    
    formatted = []
    for author in authors:
        given = author.get('given', '')
        family = author.get('family', '')
        
        if family:
            # Tomar solo iniciales del nombre
            initials = ''.join([name[0] + '.' for name in given.split() if name]) if given else ''
            formatted.append(f"{family}, {initials}".strip())
    
    return ', '.join(formatted) if formatted else None

