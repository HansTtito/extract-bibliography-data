import re
import pdfplumber
from typing import List, Dict, Optional
from io import BytesIO
from app.services.reference_parser import ReferenceParser


class ReferencesPDFExtractor:
    """Servicio para extraer múltiples referencias bibliográficas de un PDF"""
    
    def __init__(self):
        self.reference_parser = ReferenceParser()
    
    def extract_references(self, pdf_content: bytes) -> List[str]:
        """Extrae todas las referencias bibliográficas de un PDF"""
        references = []
        
        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                # Intentar extraer texto manteniendo estructura de columnas
                full_text = ""
                pages_text = []
                
                for page in pdf.pages:
                    # Extraer texto simple
                    page_text = page.extract_text()
                    if page_text:
                        pages_text.append(page_text)
                        full_text += page_text + "\n"
                    
                    # Intentar extraer por columnas si es posible
                    # Esto ayuda con PDFs de dos columnas
                    try:
                        # Obtener palabras con sus posiciones
                        words = page.extract_words()
                        if words:
                            # Ordenar por posición Y (vertical) y luego X (horizontal)
                            # Esto ayuda a mantener el orden correcto en dos columnas
                            words_sorted = sorted(words, key=lambda w: (w['top'], w['x0']))
                            # Reconstruir texto ordenado
                            column_text = ' '.join([w['text'] for w in words_sorted])
                            if len(column_text) > len(page_text or ''):
                                # Si el texto ordenado es más largo, puede ser mejor
                                pass  # Por ahora usamos el texto simple
                    except:
                        pass
                
                if not full_text:
                    return references
                
                # Buscar sección de referencias
                ref_section_patterns = [
                    r'REFERENCES\s*\n',
                    r'References\s*\n',
                    r'LITERATURE\s+CITED\s*\n',
                    r'Bibliography\s*\n',
                    r'REFERENCIAS\s*\n',
                    r'Bibliografía\s*\n',
                ]
                
                ref_section_start = None
                for pattern in ref_section_patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        ref_section_start = match.end()
                        break
                
                # Si no se encuentra sección específica, buscar desde el final
                # (las referencias suelen estar al final del documento)
                if ref_section_start is None:
                    # Buscar en las últimas páginas
                    if len(pages_text) > 2:
                        # Usar las últimas 3 páginas como referencia
                        ref_section = '\n'.join(pages_text[-3:])
                    else:
                        ref_section = full_text
                else:
                    ref_section = full_text[ref_section_start:]
                
                # Detectar y eliminar secciones que NO son referencias
                # Estas secciones suelen aparecer después de las referencias
                end_section_keywords = [
                    'FUNDING', 'Funding',
                    'ACKNOWLEDGMENTS', 'Acknowledgments', 'ACKNOWLEDGMENT', 'Acknowledgment',
                    'DATA AVAILABILITY', 'Data Availability',
                    'SUPPLEMENTARY MATERIAL', 'Supplementary Material',
                    'AUTHOR CONTRIBUTIONS', 'Author Contributions',
                    'CONFLICT OF INTEREST', 'Conflict of Interest',
                    'REFERENCES CITED', 'References Cited',
                    'SUPPLEMENTARY FIGURE', 'Supplementary Figure',
                ]
                
                # Buscar la primera aparición de estas secciones y cortar ahí
                lines = ref_section.split('\n')
                filtered_lines = []
                found_end_section = False
                
                for i, line in enumerate(lines):
                    line_upper = line.upper().strip()
                    line_stripped = line.strip()
                    
                    # Si encontramos una de estas secciones, cortar
                    for keyword in end_section_keywords:
                        # Buscar como palabra completa o al inicio de línea
                        if (keyword.upper() == line_upper or 
                            line_upper.startswith(keyword.upper() + ' ') or
                            line_upper.startswith(keyword.upper() + '\n')):
                            if len(line_stripped) < 100:  # Probablemente es un header
                                found_end_section = True
                                break
                    
                    # También detectar frases que indican fin de referencias
                    if any(phrase in line_upper for phrase in [
                        'THIS RESEARCH WAS SPONSORED',
                        'WE APPRECIATE',
                        'THE ORIGINAL CONTRIBUTIONS',
                        'FURTHER INQUIRIES CAN BE',
                        'SUPPLEMENTARY FIGURE',
                        'ENDORSED BY THE PUBLISHER',
                        'NO USE, DISTRIBUTION OR REPRODUCTION',
                    ]):
                        found_end_section = True
                        break
                    
                    if found_end_section:
                        break
                    
                    filtered_lines.append(line)
                
                ref_section = '\n'.join(filtered_lines)
                
                # También eliminar texto que claramente no es una referencia
                # (como "Frontiers in Marine Science", números de página, etc.)
                lines = ref_section.split('\n')
                filtered_lines = []
                skip_patterns = [
                    r'^Frontiers\s+in\s+Marine\s+Science',
                    r'^Volume\s+\d+',
                    r'^Article\s+\d+',
                    r'^www\.frontiersin\.org',
                    r'^doi:\s*10\.',
                    r'^https?://',
                    r'^\d+$',  # Solo números (números de página)
                    r'^Page\s+\d+',
                ]
                
                for line in lines:
                    should_skip = False
                    line_upper = line.upper().strip()
                    
                    # Verificar patrones de skip
                    for pattern in skip_patterns:
                        if re.match(pattern, line, re.IGNORECASE):
                            should_skip = True
                            break
                    
                    # Verificar frases que indican que no es una referencia
                    if not should_skip:
                        if any(phrase in line_upper for phrase in [
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
                            'NO USE, DISTRIBUTION',
                        ]):
                            should_skip = True
                    
                    if not should_skip:
                        filtered_lines.append(line)
                
                ref_section = '\n'.join(filtered_lines)
                
                # Dividir en referencias individuales
                reference_lines = self._split_into_references(ref_section)
                
                # Procesar cada referencia potencial
                for ref_text in reference_lines:
                    ref_text = ref_text.strip()
                    
                    # Validaciones básicas
                    if len(ref_text) < 50:  # Muy corta, probablemente no es referencia
                        continue
                    
                    # Debe tener un año válido
                    if not re.search(r'\b(19\d{2}|20[0-2]\d)\b', ref_text):
                        continue
                    
                    # No debe ser solo texto de funding/acknowledgments
                    ref_upper = ref_text.upper()
                    if any(phrase in ref_upper for phrase in [
                        'THIS RESEARCH WAS SPONSORED',
                        'FONDAP-CONICYT',
                        'FONDEQUIP',
                        'FONDECYT',
                        'WE APPRECIATE THE ADVICE',
                        'THE ORIGINAL CONTRIBUTIONS PRESENTED',
                        'FURTHER INQUIRIES CAN BE DIRECTED',
                        'SUPPLEMENTARY MATERIAL FOR THIS ARTICLE',
                        'AUTHOR CONTRIBUTIONS',
                        'ENDORSED BY THE PUBLISHER',
                    ]):
                        continue
                    
                    references.append(ref_text)
        
        except Exception as e:
            print(f"Error extrayendo referencias del PDF: {e}")
        
        return references
    
    def _split_into_references(self, text: str) -> List[str]:
        """Divide el texto en referencias individuales"""
        references = []
        
        # Normalizar saltos de línea
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\r', '\n', text)
        
        # Limpiar headers y footers comunes
        text = re.sub(r'Frontiers in Marine Science.*?\n', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Volume \d+.*?\n', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Article \d+.*?\n', '', text, flags=re.IGNORECASE)
        text = re.sub(r'www\.frontiersin\.org.*?\n', '', text, flags=re.IGNORECASE)
        
        # Dividir por líneas
        lines = text.split('\n')
        
        current_ref = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if not line:
                # Si hay una referencia acumulada, guardarla
                if current_ref:
                    ref_text = ' '.join(current_ref)
                    if len(ref_text) > 50:
                        references.append(ref_text)
                    current_ref = []
                continue
            
            # Detectar si es inicio de nueva referencia
            is_new_ref = False
            
            # Primero, validar que NO es un header/footer o sección no relevante
            if re.match(r'^(Frontiers|Volume|Article|doi:|http|www\.|FUNDING|ACKNOWLEDGMENTS?|DATA AVAILABILITY|SUPPLEMENTARY|AUTHOR CONTRIBUTIONS)', line, re.IGNORECASE):
                continue
            
            # Patrón 1: Apellido, Inicial. (año) o Apellido, Inicial., año
            # Ejemplo: "Aguilera, V., Escribano, R., and Herrera, L. (2009)"
            if re.match(r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?,\s*[A-Z]', line):
                is_new_ref = True
            # Patrón 2: Apellido (año) o Apellido, año
            elif re.match(r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?[\s,]*\(?\d{4}', line):
                is_new_ref = True
            # Patrón 3: Número seguido de punto (referencias numeradas)
            elif re.match(r'^\d+\.\s+[A-Z]', line):
                is_new_ref = True
            # Patrón 4: Línea que empieza con apellido seguido directamente de año
            elif re.match(r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+\d{4}', line) and len(line) > 20:
                is_new_ref = True
            
            if is_new_ref and current_ref:
                # Guardar referencia anterior
                ref_text = ' '.join(current_ref)
                # Limpiar espacios múltiples
                ref_text = re.sub(r'\s+', ' ', ref_text).strip()
                if len(ref_text) > 50:
                    references.append(ref_text)
                current_ref = [line]
            else:
                # Continuar referencia actual
                current_ref.append(line)
        
        # Agregar última referencia
        if current_ref:
            ref_text = ' '.join(current_ref)
            ref_text = re.sub(r'\s+', ' ', ref_text).strip()
            if len(ref_text) > 50:
                references.append(ref_text)
        
        # Limpiar referencias finales (eliminar headers, footers, etc.)
        cleaned_refs = []
        exclude_patterns = [
            r'^Frontiers',
            r'^Volume \d+',
            r'^Article \d+',
            r'^doi:',
            r'^http',
            r'^www\.',
            r'^\d+$',  # Solo números
            r'^FUNDING',
            r'^ACKNOWLEDGMENTS?',
            r'^DATA AVAILABILITY',
            r'^SUPPLEMENTARY MATERIAL',
            r'^AUTHOR CONTRIBUTIONS',
            r'^CONFLICT OF INTEREST',
            r'High-FrequencyVariabilityofCoastalUpwelling',  # Texto mal extraído
            r'FUNDING',  # Sección de funding
            r'ACKNOWLEDGMENTS',  # Sección de acknowledgments
        ]
        
        # Patrones que indican que NO es una referencia válida
        invalid_ref_patterns = [
            r'^(FUNDING|Funding|ACKNOWLEDGMENTS?|Acknowledgments?|DATA AVAILABILITY|Data Availability)',
            r'High-FrequencyVariabilityofCoastalUpwelling.*?FUNDING',  # Texto concatenado incorrecto
            r'^[A-Z][a-z]+Variabilityof[A-Z]',  # Palabras concatenadas sin espacios (error de extracción)
            r'^[A-Z][a-z]+of[A-Z][a-z]+',  # Más palabras concatenadas
            r'doi:10\.\d+/[A-Z]',  # DOI mal formado al inicio
        ]
        
        for ref in references:
            should_exclude = False
            
            # Verificar patrones de exclusión
            for pattern in exclude_patterns:
                if re.search(pattern, ref, re.IGNORECASE):
                    should_exclude = True
                    break
            
            # Verificar patrones de referencia inválida
            if not should_exclude:
                for pattern in invalid_ref_patterns:
                    if re.search(pattern, ref, re.IGNORECASE):
                        should_exclude = True
                        break
            
            # Validaciones adicionales
            if not should_exclude:
                # Debe tener al menos un año válido (1900-2024)
                if not re.search(r'\b(19\d{2}|20[0-2]\d)\b', ref):
                    should_exclude = True
                
                # No debe ser demasiado corta (menos de 30 caracteres) ni demasiado larga (más de 2000)
                if len(ref) < 30 or len(ref) > 2000:
                    should_exclude = True
                
                # No debe tener demasiadas palabras concatenadas sin espacios (error de extracción PDF)
                # Contar secuencias de mayúsculas seguidas de minúsculas sin espacios
                concatenated_words = len(re.findall(r'[a-záéíóúñ][A-ZÁÉÍÓÚÑ]', ref))
                if concatenated_words > 5:
                    should_exclude = True
                
                # No debe contener texto que claramente no es una referencia
                # (como "This research was sponsored", "We appreciate", etc.)
                invalid_phrases = [
                    'This research was sponsored',
                    'We appreciate',
                    'The original contributions',
                    'further inquiries can be directed',
                    'Supplementary Figure',
                    'The Supplementary Material',
                    'Any product that may be evaluated',
                    'endorsed by the publisher',
                    'No use, distribution or reproduction',
                ]
                ref_lower = ref.lower()
                for phrase in invalid_phrases:
                    if phrase.lower() in ref_lower:
                        should_exclude = True
                        break
            
            if not should_exclude:
                # Agregar espacios donde faltan (corregir extracción PDF)
                # Patrón 1: minúscula seguida de mayúscula = falta espacio
                ref = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', ref)
                # Patrón 2: número seguido de letra (sin espacio)
                ref = re.sub(r'(\d)([A-Za-z])', r'\1 \2', ref)
                # Patrón 3: letra seguida de número cuando debería haber espacio
                ref = re.sub(r'([A-Za-z])(\d{4,})', r'\1 \2', ref)
                # Patrón 4: palabras comunes concatenadas (ej: "ofCoastal" -> "of Coastal")
                ref = re.sub(r'([a-z])([A-Z][a-z]+)', r'\1 \2', ref)
                # Limpiar espacios múltiples
                ref = re.sub(r'\s+', ' ', ref).strip()
                
                # Validar que después de agregar espacios, sigue siendo una referencia válida
                # Debe tener al menos un año válido después de la corrección
                if re.search(r'\b(19\d{2}|20[0-2]\d)\b', ref):
                    cleaned_refs.append(ref)
        
        return cleaned_refs

