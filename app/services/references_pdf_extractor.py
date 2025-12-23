import re
import pdfplumber
import logging
from typing import List, Dict, Optional
from io import BytesIO
from app.services.reference_parser import ReferenceParser
from app.services.grobid_service import GrobidService
from app.utils.patterns import BiblioPatterns, TextNormalizer
from app.utils.text_processing import normalize_text_spacing

logger = logging.getLogger(__name__)


class ReferencesPDFExtractor:
    """Servicio para extraer múltiples referencias bibliográficas de un PDF"""
    
    def __init__(self):
        self.reference_parser = ReferenceParser()
        self.grobid_service = GrobidService()
    
    def _normalize_text_spacing(self, text: str) -> str:
        """
        Normaliza texto agregando espacios entre palabras concatenadas.
        CRÍTICO: Debe aplicarse ANTES de dividir referencias.
        """
        # Normalizar espacios entre palabras concatenadas
        text = normalize_text_spacing(text)
        
        # MEJORADO: Normalizar espacios después de comas en autores (ej: "Aguilera,V." -> "Aguilera, V.")
        # Patrón más específico: Apellido,Inicial -> Apellido, Inicial
        text = re.sub(r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}),([A-ZÁÉÍÓÚÑ])', r'\1, \2', text)
        
        # MEJORADO: Normalizar espacios después de comas en listas de autores
        # Ej: "Aguilera,V.,Escribano,R." -> "Aguilera, V., Escribano, R."
        text = re.sub(r'([a-záéíóúñ]),([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})', r'\1, \2', text)
        
        # Normalizar espacios después de puntos seguidos de mayúscula
        # Ej: "J.Mar.Syst" -> "J. Mar. Syst"
        text = re.sub(r'([A-Z])\.([A-Z])', r'\1. \2', text)
        
        # MEJORADO: Normalizar palabras concatenadas comunes en títulos
        # Ej: "Highfrequency" -> "High frequency", "nanoplanktonandmicroplankton" -> "nanoplankton and microplankton"
        text = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,})', r'\1 \2', text)
        
        # Limpiar espacios múltiples
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_references(self, pdf_content: bytes) -> List[str]:
        """
        Extrae todas las referencias bibliográficas de un PDF
        Estrategia: GROBID primero, fallback a regex si falla o calidad baja
        """
        # 1. Intentar GROBID primero (si está disponible)
        if self.grobid_service.use_grobid:
            grobid_refs = self.grobid_service.extract_references_from_pdf(pdf_content)
            if grobid_refs and len(grobid_refs) > 0:
                # Validar calidad de GROBID
                if self._validate_grobid_quality(grobid_refs):
                    logger.info(f"GROBID extrajo {len(grobid_refs)} referencias")
                    # Convertir a formato texto para compatibilidad
                    text_refs = self.grobid_service._convert_grobid_to_text(grobid_refs)
                    return text_refs
                else:
                    logger.warning("GROBID calidad baja, usando fallback a regex")
        
        # 2. Fallback a método actual (regex)
        return self._extract_with_regex(pdf_content)
    
    def _validate_grobid_quality(self, grobid_refs: List[Dict]) -> bool:
        """
        Valida que GROBID extrajo información suficiente
        
        Args:
            grobid_refs: Lista de referencias de GROBID
            
        Returns:
            True si la calidad es aceptable, False en caso contrario
        """
        if not grobid_refs:
            return False
        
        # Verificar que al menos 70% tienen título y año
        valid_count = sum(
            1 for ref in grobid_refs
            if ref.get('title') and len(ref.get('title', '')) > 10
            and ref.get('year')
        )
        
        quality_ratio = valid_count / len(grobid_refs) if grobid_refs else 0
        return quality_ratio >= 0.7
    
    def _extract_with_regex(self, pdf_content: bytes) -> List[str]:
        """Extrae referencias usando el método regex (fallback)"""
        references = []
        
        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                # Intentar extraer texto manteniendo estructura de columnas
                full_text = ""
                pages_text = []
                
                for page in pdf.pages:
                    page_text = None
                    
                    # MEJORADO: Intentar extraer por palabras primero (mejor para columnas)
                    try:
                        words = page.extract_words()
                        if words and len(words) > 50:  # Si hay suficientes palabras
                            # Detectar si hay dos columnas
                            mid_point = page.width / 2
                            left_words = [w for w in words if w['x0'] < mid_point]
                            right_words = [w for w in words if w['x0'] >= mid_point]
                            
                            # Si ambas columnas tienen contenido significativo
                            if len(left_words) > 20 and len(right_words) > 20:
                                # Ordenar cada columna por posición Y (vertical)
                                left_sorted = sorted(left_words, key=lambda w: w['top'])
                                right_sorted = sorted(right_words, key=lambda w: w['top'])
                                
                                # Combinar: primero columna izquierda completa, luego derecha
                                left_text = ' '.join([w['text'] for w in left_sorted])
                                right_text = ' '.join([w['text'] for w in right_sorted])
                                page_text = left_text + '\n' + right_text
                            else:
                                # Una columna: ordenar por Y y luego X
                                words_sorted = sorted(words, key=lambda w: (w['top'], w['x0']))
                                page_text = ' '.join([w['text'] for w in words_sorted])
                    except Exception as e:
                        print(f"Error al extraer por palabras: {e}")
                    
                    # Fallback: extraer texto simple
                    if not page_text:
                        page_text = page.extract_text()
                    
                    if page_text:
                        pages_text.append(page_text)
                        full_text += page_text + "\n"
                
                if not full_text:
                    return references
                
                # Normalizar texto ANTES de buscar sección (agregar espacios entre palabras concatenadas)
                normalized_text = self._normalize_text_spacing(full_text)
                
                # Buscar sección de referencias con patrones más flexibles
                
                ref_section_patterns = [
                    r'REFERENCES\s*\n',
                    r'References\s*\n',
                    r'LITERATURE\s+CITED\s*\n',
                    r'Bibliography\s*\n',
                    r'REFERENCIAS\s*\n',
                    r'Bibliografía\s*\n',
                    r'References\s+and\s+Notes',  # Algunos formatos
                    r'Works\s+Cited',  # Formato MLA
                    r'Bibliography\s+and\s+References',
                ]
                
                # DEBUG: Verificar textos disponibles
                print(f"\n🔍 DEBUG: Longitudes de texto:")
                print(f"  - full_text: {len(full_text)} caracteres")
                print(f"  - normalized_text: {len(normalized_text)} caracteres")
                print(f"  - pages_text: {len(pages_text)} páginas")
                
                # Buscar sección de referencias - VERSIÓN SIMPLIFICADA
                ref_section = None
                ref_section_start = None
                
                # 1. Buscar "REFERENCES" en texto normalizado primero
                ref_match = re.search(r'\bREFERENCES\b', normalized_text, re.IGNORECASE)
                if ref_match:
                    ref_section_start = ref_match.end()
                    ref_section = normalized_text[ref_section_start:]
                    print(f"✅ REFERENCES encontrado en normalized_text en posición {ref_match.start()}")
                    print(f"📏 Texto de referencias desde normalized_text: {len(ref_section)} caracteres")
                    print(f"📝 Muestra (primeros 300 chars): {ref_section[:300]}")
                
                # 2. Si no encontró o está vacío, buscar en full_text original
                if not ref_section or len(ref_section.strip()) < 100:
                    print("⚠️  Búsqueda en normalized_text falló o está vacío, intentando full_text...")
                    ref_match = re.search(r'\bREFERENCES\b', full_text, re.IGNORECASE)
                    if ref_match:
                        ref_section = full_text[ref_match.end():]
                        print(f"✅ Usando full_text desde posición {ref_match.end()}: {len(ref_section)} caracteres")
                        print(f"📝 Muestra (primeros 300 chars): {ref_section[:300]}")
                        # Normalizar este texto
                        ref_section = self._normalize_text_spacing(ref_section)
                        print(f"📏 Después de normalizar: {len(ref_section)} caracteres")
                
                # 3. Si aún no hay nada, usar últimas páginas
                if not ref_section or len(ref_section.strip()) < 100:
                    print("⚠️  No se encontró REFERENCES o está vacío, usando últimas 3 páginas...")
                    if len(pages_text) > 2:
                        ref_section = '\n'.join(pages_text[-3:])
                        ref_section = self._normalize_text_spacing(ref_section)
                        print(f"📏 Usando últimas 3 páginas: {len(ref_section)} caracteres")
                    else:
                        ref_section = full_text
                        ref_section = self._normalize_text_spacing(ref_section)
                        print(f"📏 Usando todo el texto: {len(ref_section)} caracteres")
                
                print(f"📊 FINAL: ref_section tiene {len(ref_section)} caracteres")
                if len(ref_section) > 0:
                    print(f"📝 Primeros 500 caracteres: {ref_section[:500]}")
                
                # DEBUG: Verificar si el texto tiene saltos de línea
                lines_before_filter = ref_section.split('\n')
                print(f"🔍 DEBUG: Líneas antes del filtrado: {len(lines_before_filter)}")
                
                # Si está todo en una línea, solo cortar secciones finales y saltar filtrado
                if len(lines_before_filter) <= 1:
                    print(f"⚠️  El texto está todo en una línea (sin saltos de línea)")
                    print(f"   Esto es normal para PDFs extraídos. Solo cortaremos secciones finales.")
                    # Solo buscar y cortar si encuentra secciones finales
                    end_section_pos = None
                    found_keyword = None
                    end_section_keywords = [
                        'FUNDING', 'ACKNOWLEDGMENTS', 'DATA AVAILABILITY',
                        'SUPPLEMENTARY MATERIAL', 'AUTHOR CONTRIBUTIONS'
                    ]
                    for keyword in end_section_keywords:
                        pos = ref_section.upper().find(keyword)
                        if pos != -1 and (end_section_pos is None or pos < end_section_pos):
                            end_section_pos = pos
                            found_keyword = keyword
                    
                    if end_section_pos:
                        ref_section = ref_section[:end_section_pos]
                        print(f"   Cortado en posición {end_section_pos} (encontrado: {found_keyword})")
                    
                    # Saltar TODO el filtrado de líneas y ir directo a dividir referencias
                    print(f"📏 Texto después de cortar secciones finales: {len(ref_section)} caracteres")
                    # Saltar al final del bloque de filtrado
                else:
                    # El texto tiene múltiples líneas, aplicar filtrado normal
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
                    print(f"📏 Texto después del primer filtrado: {len(ref_section)} caracteres")
                    
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
                    print(f"📏 Texto después del segundo filtrado: {len(ref_section)} caracteres")
                
                # DEBUG: Mostrar muestra del texto de referencias (después de todo el filtrado)
                print(f"\n📝 Muestra del texto de referencias (primeros 500 caracteres):")
                print(f"{ref_section[:500]}...")
                print(f"📏 Longitud total del texto de referencias: {len(ref_section)} caracteres\n")
                
                # Dividir en referencias individuales
                reference_lines = self._split_into_references(ref_section)
                print(f"Referencias potenciales encontradas después de dividir: {len(reference_lines)}")
                
                # DEBUG: Mostrar las primeras referencias encontradas
                if reference_lines:
                    print(f"\n📋 Primeras 3 referencias encontradas:")
                    for i, ref in enumerate(reference_lines[:3], 1):
                        print(f"  {i}. Longitud: {len(ref)} chars - {ref[:100]}...")
                else:
                    print(f"\n⚠️  No se encontraron referencias. Revisando por qué...")
                    # Intentar detectar si hay años en el texto
                    years = re.findall(BiblioPatterns.YEAR_FULL, ref_section)
                    print(f"  - Años encontrados en el texto: {len(years)} ({years[:5] if years else 'ninguno'})")
                    # Intentar detectar si hay autores
                    authors = re.findall(BiblioPatterns.AUTHOR_SEARCH, ref_section)
                    print(f"  - Patrones de autor encontrados: {len(authors)}")
                    if authors:
                        print(f"    Ejemplos: {authors[:3]}")
                
                # Procesar cada referencia potencial
                for ref_text in reference_lines:
                    ref_text = ref_text.strip()
                    
                    # DEBUG: Mostrar referencia antes de limpiar
                    if len(ref_text) > 50:
                        print(f"  Referencia candidata (antes de limpiar): {ref_text[:150]}...")
                    
                    # MEJORADO: Limpiar basura al inicio de la referencia
                    ref_text_cleaned = self._clean_reference_start(ref_text)
                    
                    # DEBUG: Mostrar después de limpiar
                    if len(ref_text_cleaned) > 50:
                        print(f"  Referencia candidata (después de limpiar): {ref_text_cleaned[:150]}...")
                    
                    # Validaciones básicas (más flexibles)
                    if len(ref_text_cleaned) < 50:  # Reducido a 50 para ser más flexible
                        print(f"  ❌ Rechazada: muy corta ({len(ref_text_cleaned)} caracteres)")
                        continue
                    
                    # Debe tener un año válido
                    if not re.search(BiblioPatterns.YEAR_FULL, ref_text_cleaned):
                        print(f"  ❌ Rechazada: no tiene año válido")
                        continue
                    
                    # No debe ser solo texto de funding/acknowledgments
                    if BiblioPatterns.contains_invalid_phrase(ref_text_cleaned):
                        print(f"  ❌ Rechazada: contiene frase inválida")
                        continue
                    
                    print(f"  ✅ Referencia aceptada: {len(ref_text_cleaned)} caracteres")
                    references.append(ref_text_cleaned)
                
                print(f"Referencias válidas después de validación: {len(references)}")
        
        except Exception as e:
            print(f"Error extrayendo referencias del PDF: {e}")
            import traceback
            traceback.print_exc()
        
        return references
    
    def _split_into_references(self, text: str) -> List[str]:
        """Divide el texto en referencias individuales"""
        references = []
        
        # PASO 1: Normalizar saltos de línea
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\r', '\n', text)
        
        # PASO 2: Normalizar espacios ANTES de dividir (CRÍTICO para palabras concatenadas)
        text = self._normalize_text_spacing(text)
        
        # PASO 3: Limpiar headers y footers comunes
        text = re.sub(r'Frontiers in Marine Science.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Volume \d+.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Article \d+.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'www\.frontiersin\.org.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
        
        # PASO 4: CLAVE - Detectar si todo está en una línea o múltiples líneas
        lines = text.split('\n')
        
        # DEBUG: Mostrar estadísticas
        print(f"  🔍 Procesando {len(lines)} líneas en _split_into_references")
        if len(lines) > 0:
            print(f"  📄 Primera línea: {len(lines[0])} chars - '{lines[0][:80]}...'")
        
        # Si hay solo 1 línea muy larga (más de 500 chars), probablemente las referencias están todas juntas
        if len(lines) == 1 and len(lines[0]) > 500:
            print(f"  ⚠️  Detectado: todas las referencias en 1 línea ({len(lines[0])} chars)")
            print(f"  🔧 Aplicando split por patrón de inicio de referencia...")
            
            # MEJORADO: Buscar donde empieza una referencia completa
            # Patrón: Apellido, Inicial. seguido de (año) o continuación con "and" o ","
            # Debe estar precedido por el final de otra referencia (doi, páginas, etc.)
            # Usamos lookbehind negativo para NO capturar autores en medio de una referencia
            
            # Buscar terminaciones de referencias (doi, páginas, año)
            # Luego buscar el siguiente autor
            pattern = r'(?:^|\.\s|\)\.?\s|doi:[^\s]+\s|[\d]+–[\d]+\.?\s)([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,},\s*[A-Z]\.)'
            
            matches = list(re.finditer(pattern, lines[0]))
            print(f"  ✅ Encontrados {len(matches)} inicios de referencia potenciales")
            
            if matches and len(matches) > 1:  # Necesitamos al menos 2 para dividir
                refs_extracted = []
                for i, match in enumerate(matches):
                    # Empezar desde donde comienza el apellido (group 1)
                    start = match.start(1)
                    # El final es el inicio de la siguiente referencia (o el final del texto)
                    end = matches[i + 1].start(1) if i + 1 < len(matches) else len(lines[0])
                    ref_text = lines[0][start:end].strip()
                    
                    if len(ref_text) > 50:  # Filtro básico de longitud
                        refs_extracted.append(ref_text)
                        if i < 3:  # Debug: mostrar primeras 3
                            print(f"    {i+1}. {ref_text[:100]}...")
                
                if refs_extracted:
                    print(f"  ✅ Extraídas {len(refs_extracted)} referencias del texto consolidado")
                    return refs_extracted
            
            # Si no funcionó, intentar método más agresivo
            print(f"  ⚠️  Método 1 no funcionó, probando método alternativo...")
            
            # Método 2: Buscar patrón más simple - solo al inicio o después de punto/doi
            simple_pattern = r'(?:^|\.doi:[^\s]+\s+|[\d]+–[\d]+\.\s+|[\d]{4}\)\.\s*)([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{3,},\s*[A-Z]\.)'
            matches2 = list(re.finditer(simple_pattern, lines[0]))
            print(f"  Encontrados {len(matches2)} inicios (método 2)")
            
            if matches2 and len(matches2) > 1:
                refs_extracted = []
                for i, match in enumerate(matches2):
                    start = match.start(1)
                    end = matches2[i + 1].start(1) if i + 1 < len(matches2) else len(lines[0])
                    ref_text = lines[0][start:end].strip()
                    
                    if len(ref_text) > 50:
                        refs_extracted.append(ref_text)
                        if i < 3:
                            print(f"    {i+1}. {ref_text[:100]}...")
                
                if refs_extracted:
                    print(f"  ✅ Extraídas {len(refs_extracted)} referencias (método 2)")
                    return refs_extracted
            
            # Último recurso: dividir por años
            print(f"  ⚠️  Usando último recurso: dividir por años...")
            year_pattern = r'(\(\d{4}\)|\s\d{4}[\.,])'
            parts = re.split(year_pattern, lines[0])
            print(f"  🔧 Dividiendo por años: {len(parts)} partes")
            
            # Reconstruir referencias juntando parte + año
            for i in range(0, len(parts) - 1, 2):
                if i + 1 < len(parts):
                    ref_text = (parts[i] + parts[i + 1]).strip()
                    if len(ref_text) > 50:
                        references.append(ref_text)
            
            return references
        
        # Si hay múltiples líneas, usar el método original (línea por línea)
        current_ref = []
        new_ref_count = 0
        
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
            if BiblioPatterns.is_header(line) or BiblioPatterns.is_section(line):
                continue
            
            # Si es "REFERENCES" o "References", limpiar referencia actual y continuar
            if BiblioPatterns.is_reference_section(line):
                # Limpiar referencia actual si existe (no debe incluir "REFERENCES")
                if current_ref:
                    ref_text = ' '.join(current_ref)
                    ref_text = re.sub(r'\s+', ' ', ref_text).strip()
                    if self._is_valid_reference(ref_text):
                        references.append(ref_text)
                    current_ref = []
                continue
            
            # CRITERIO PRINCIPAL: Una referencia nueva debe empezar con un autor completo
            # MEJORADO: Patrón más flexible que busca autor en cualquier parte de la línea
            # Patrón 1: Apellido, Inicial. (año) - Buscar en toda la línea, no solo al inicio
            # Ejemplo: "Aguilera, V., Escribano, R., and Herrera, L. (2009)"
            # Buscar patrón de autor en la línea (puede tener basura antes)
            if re.search(BiblioPatterns.AUTHOR_SEARCH, line):
                # Verificar que tiene año válido
                if re.search(BiblioPatterns.YEAR_FULL, line):
                    # Verificar que NO es solo parte de una referencia anterior
                    # Excluir casos como "America, 1967-73" (solo apellido y año con guión)
                    if not re.search(BiblioPatterns.AUTHOR_YEAR_RANGE_EXCLUDE, line):
                        # Verificar que tiene estructura de autor completo (al menos inicial después de coma)
                        if re.search(BiblioPatterns.AUTHOR_COMMA_INITIAL, line):
                            is_new_ref = True
                            new_ref_count += 1
                            if new_ref_count <= 3:  # Debug: mostrar primeras 3 detecciones
                                print(f"    ✅ Nueva referencia detectada (línea {i}): '{line[:80]}...'")
            # Patrón 2: Apellido, Inicial., año (sin paréntesis, con múltiples autores)
            # Ejemplo: "Aguilera, V., Escribano, R., 2009"
            elif re.search(BiblioPatterns.AUTHOR_MULTIPLE_COMMA, line):
                # Verificar que tiene año después
                if re.search(BiblioPatterns.YEAR_FULL, line):
                    is_new_ref = True
            # Patrón 3: Número seguido de punto (referencias numeradas)
            # Ejemplo: "1. Aguilera, V., ..."
            elif re.match(BiblioPatterns.REF_NUMBERED, line):
                is_new_ref = True
            # NO usar patrón flexible que detecta cualquier línea con año
            # Esto causa divisiones incorrectas como "America, 1967-73"
            
            if is_new_ref and current_ref:
                # Guardar referencia anterior
                ref_text = ' '.join(current_ref)
                # Limpiar espacios múltiples
                ref_text = TextNormalizer.clean_multiple_spaces(ref_text)
                # Validación más flexible: solo verificar longitud mínima
                if len(ref_text) > 50:
                    references.append(ref_text)
                # Iniciar nueva referencia
                current_ref = [line]
            else:
                # Continuar referencia actual
                # Solo agregar si no es una línea muy corta que probablemente es ruido
                if len(line) > 3 or (current_ref and len(' '.join(current_ref)) > 50):
                    current_ref.append(line)
        
        # Agregar última referencia
        if current_ref:
            ref_text = ' '.join(current_ref)
            ref_text = TextNormalizer.clean_multiple_spaces(ref_text)
            # Validación más flexible: solo verificar longitud mínima
            if len(ref_text) > 50:
                references.append(ref_text)
        
        return references
    
    def _clean_reference_start(self, ref_text: str) -> str:
        """
        Limpia basura al inicio de la referencia.
        Remueve frases comunes que aparecen antes de la referencia real.
        """
        # Patrones de texto basura al inicio
        garbage_patterns = [
            r'^and\s+approved\s+the\s+submitted\s+version\.?\s*',
            r'^submitted\s+version\.?\s*',
            r'^approved\s+the\s+submitted\.?\s*',
            r'^and\s+approved\.?\s*',
            r'^REFERENCES\s+',
            r'^References\s+',
            r'^\.\s*',  # Punto al inicio
            r'^,\s*',  # Coma al inicio
        ]
        
        for pattern in garbage_patterns:
            ref_text = re.sub(pattern, '', ref_text, flags=re.IGNORECASE).strip()
        
        # Buscar el primer patrón de autor válido y cortar todo lo anterior
        # Formato: "Apellido, Inicial." o "Apellido, Inicial.,"
        # MEJORADO: Usa patrón centralizado
        author_match = re.search(BiblioPatterns.AUTHOR_SEARCH, ref_text)
        if author_match:
            # Si encontramos un autor, tomar desde ahí
            ref_text = ref_text[author_match.start():]
        
        return ref_text.strip()
    
    def _is_valid_reference(self, ref_text: str) -> bool:
        """
        Valida si un texto es una referencia bibliográfica válida
        MEJORADO: Validación más robusta con criterios más estrictos
        """
        ref_text = ref_text.strip()
        
        # Criterio 1: Longitud mínima (flexible para capturar referencias completas)
        if len(ref_text) < 50:  # Reducido a 50 para ser más flexible
            return False
        
        # Criterio 2: Debe tener un año válido
        if not re.search(BiblioPatterns.YEAR_FULL, ref_text):
            return False
        
        # Criterio 3: No debe empezar con palabras que indican que no es una referencia
        if BiblioPatterns.is_header(ref_text) or BiblioPatterns.is_section(ref_text) or BiblioPatterns.is_reference_section(ref_text):
            return False
        
        # Criterio 4: Debe tener al menos un patrón de autor completo
        # Formato: "Apellido, Inicial." o "Apellido Inicial."
        # MEJORADO: Usa patrones centralizados
        has_author = (
            re.search(BiblioPatterns.AUTHOR_SEARCH, ref_text) or
            re.search(BiblioPatterns.AUTHOR_NO_COMMA, ref_text)
        )
        if not has_author:
            return False
        
        # Criterio 5: No debe ser solo números o metadata
        if re.match(r'^\d+$', ref_text) or re.match(r'^[A-Z\s]{1,30}$', ref_text):
            return False
        
        # Criterio 6: No debe contener frases comunes de funding/acknowledgments
        if BiblioPatterns.contains_invalid_phrase(ref_text):
            return False
                
        # Criterio 7: Debe tener estructura mínima de referencia
        # Debe tener al menos: Autor + Año + algo más (título, revista, etc.)
        year_pos = list(re.finditer(BiblioPatterns.YEAR_FULL, ref_text))
        if year_pos:
            # Verificar que hay texto después del año (título o revista)
            first_year_end = year_pos[0].end()
            text_after_year = ref_text[first_year_end:].strip()
            if len(text_after_year) < 20:  # Debe haber al menos 20 caracteres después del año
                return False
        
        return True

