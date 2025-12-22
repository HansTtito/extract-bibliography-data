import re
from typing import Optional, List


def extract_doi(text: str) -> Optional[str]:
    """Extrae DOI de un texto - Prioriza DOIs completos"""
    # ESTRATEGIA: Buscar DOI completo en diferentes formatos
    # Los DOIs completos son más confiables para usar con CrossRef
    
    # 1. PRIMERO: Buscar en URLs (más confiable y completo)
    url_patterns = [
        r'https?://(?:dx\.)?doi\.org/(10\.\d{4,}/[^\s\)]+)',  # URL completa
        r'doi\.org/(10\.\d{4,}/[^\s\)]+)',  # Sin http
    ]
    
    for pattern in url_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            doi = match.group(1)
            doi = doi.rstrip('.,;:)')
            if re.match(r'10\.\d{4,}/.+', doi) and len(doi.split('/')[1]) >= 5:
                return doi
    
    # 2. Buscar después de "doi:" o "DOI:" (puede estar en diferentes formatos)
    doi_label_patterns = [
        r'doi[:\s]+(10\.\d{4,}/[^\s\)]+)',  # "doi: 10.xxxx/xxxx"
        r'DOI[:\s]+(10\.\d{4,}/[^\s\)]+)',  # "DOI: 10.xxxx/xxxx"
    ]
    
    for pattern in doi_label_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            doi = match.group(1)
            doi = doi.rstrip('.,;:)')
            if re.match(r'10\.\d{4,}/.+', doi) and len(doi.split('/')[1]) >= 5:
                return doi
    
    # 3. Buscar DOI directo - Capturar el MÁS LARGO posible (más completo)
    # Patrón que captura: 10.xxxx/ seguido de alfanuméricos, puntos, guiones
    # Buscar en contexto más amplio para capturar DOI completo
    direct_pattern = r'(10\.\d{4,}/[a-zA-Z0-9\.\-]+)'
    matches = list(re.finditer(direct_pattern, text, re.IGNORECASE))
    
    if matches:
        # Ordenar por longitud (más largo = más completo)
        doi_candidates = []
        for match in matches:
            doi = match.group(1)
            doi = doi.rstrip('.,;:)')
            parts = doi.split('/')
            if len(parts) == 2 and len(parts[1]) >= 5:
                # Preferir DOIs que tengan puntos (como journal.pone.0212485)
                # o que sean razonablemente largos
                if '.' in parts[1] or len(parts[1]) >= 8:
                    doi_candidates.append((len(doi), doi))
        
        if doi_candidates:
            # Retornar el más largo
            doi_candidates.sort(reverse=True)
            return doi_candidates[0][1]
        
        # Si no hay candidatos con puntos, tomar el más largo de todos
        if matches:
            best = max(matches, key=lambda m: len(m.group(1)))
            doi = best.group(1).rstrip('.,;:)')
            if re.match(r'10\.\d{4,}/.+', doi):
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
    """Normaliza texto eliminando espacios extra y corrigiendo encoding"""
    if not text:
        return None
    
    # Corregir problemas de encoding comunes
    # Reemplazar secuencias de encoding mal formadas
    text = re.sub(r'#_#x00([A-Fa-f0-9]{2})', lambda m: chr(int(m.group(1), 16)), text)
    text = re.sub(r'#x([A-Fa-f0-9]{2,4})', lambda m: chr(int(m.group(1), 16)), text)
    
    # Eliminar espacios múltiples y saltos de línea
    text = re.sub(r'\s+', ' ', text)
    
    # Limpiar caracteres de control pero mantener caracteres especiales válidos
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    
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

