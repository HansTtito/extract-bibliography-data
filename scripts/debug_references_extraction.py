"""
Script de depuración para extraer referencias de un PDF
Uso: python debug_references_extraction.py <ruta_al_pdf>
"""
import sys
from pathlib import Path
import pdfplumber
import re

def debug_pdf_references(pdf_path: str):
    """Depura la extracción de referencias de un PDF"""
    print(f"\n{'='*60}")
    print(f"Depurando extracción de referencias del PDF: {pdf_path}")
    print(f"{'='*60}\n")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Total de páginas: {len(pdf.pages)}\n")
            
            # Extraer texto de todas las páginas
            full_text = ""
            pages_text = []
            
            for i, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
                    full_text += page_text + "\n"
                    print(f"Página {i}: {len(page_text)} caracteres")
            
            print(f"\nTotal de texto extraído: {len(full_text)} caracteres\n")
            
            # Buscar sección de referencias
            ref_section_patterns = [
                r'REFERENCES\s*\n',
                r'References\s*\n',
                r'LITERATURE\s+CITED\s*\n',
                r'Bibliography\s*\n',
                r'REFERENCIAS\s*\n',
                r'Bibliografía\s*\n',
                r'References\s+and\s+Notes',
                r'Works\s+Cited',
                r'Bibliography\s+and\s+References',
            ]
            
            print("Buscando sección de referencias...")
            ref_section_start = None
            found_pattern = None
            
            for pattern in ref_section_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    ref_section_start = match.end()
                    found_pattern = pattern
                    print(f"  ✓ Encontrado con patrón: {pattern}")
                    print(f"    Posición: {match.start()}-{match.end()}")
                    print(f"    Contexto: ...{full_text[max(0, match.start()-50):match.end()+50]}...")
                    break
            
            if ref_section_start is None:
                print("  ✗ No se encontró sección explícita de referencias")
                print("\nBuscando en últimas páginas...")
                if len(pages_text) > 2:
                    ref_section = '\n'.join(pages_text[-3:])
                    print(f"  Usando últimas 3 páginas ({len(pages_text)-2}-{len(pages_text)})")
                else:
                    ref_section = full_text
                    print(f"  Usando todo el texto")
            else:
                ref_section = full_text[ref_section_start:]
                print(f"\nSección de referencias encontrada, usando desde posición {ref_section_start}")
            
            print(f"\nLongitud de sección de referencias: {len(ref_section)} caracteres")
            
            # Buscar años en el texto
            years = re.findall(r'\b(19\d{2}|20[0-2]\d)\b', ref_section)
            print(f"\nAños encontrados en la sección: {len(years)}")
            if years:
                print(f"  Primeros 10 años: {years[:10]}")
            
            # Buscar patrones de referencias
            print("\nBuscando patrones de referencias...")
            
            # Patrón 1: Apellido, Inicial.
            pattern1_matches = re.findall(r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?,\s*[A-Z]', ref_section, re.MULTILINE)
            print(f"  Patrón 1 (Apellido, Inicial.): {len(pattern1_matches)} matches")
            if pattern1_matches:
                print(f"    Ejemplos: {pattern1_matches[:3]}")
            
            # Patrón 2: Apellido (año)
            pattern2_matches = re.findall(r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?[\s,]*\(?\d{4}', ref_section, re.MULTILINE)
            print(f"  Patrón 2 (Apellido año): {len(pattern2_matches)} matches")
            if pattern2_matches:
                print(f"    Ejemplos: {pattern2_matches[:3]}")
            
            # Patrón 3: Número. Autor
            pattern3_matches = re.findall(r'^\d+\.\s+[A-Z]', ref_section, re.MULTILINE)
            print(f"  Patrón 3 (Número. Autor): {len(pattern3_matches)} matches")
            if pattern3_matches:
                print(f"    Ejemplos: {pattern3_matches[:3]}")
            
            # Mostrar muestra del texto de referencias
            print(f"\nMuestra del texto de referencias (primeros 1000 caracteres):")
            print("-" * 60)
            print(ref_section[:1000])
            print("-" * 60)
            
            # Intentar dividir en referencias
            print("\nIntentando dividir en referencias...")
            lines = ref_section.split('\n')
            print(f"Total de líneas: {len(lines)}")
            
            # Contar líneas que parecen referencias
            ref_like_lines = 0
            for line in lines[:50]:  # Primeras 50 líneas
                line = line.strip()
                if len(line) > 30 and re.search(r'\b(19\d{2}|20[0-2]\d)\b', line):
                    ref_like_lines += 1
            
            print(f"Líneas que parecen referencias (primeras 50 líneas): {ref_like_lines}")
            
            # Mostrar algunas líneas que parecen referencias
            print("\nLíneas que parecen referencias:")
            count = 0
            for line in lines:
                line = line.strip()
                if len(line) > 30 and re.search(r'\b(19\d{2}|20[0-2]\d)\b', line):
                    print(f"  {line[:100]}...")
                    count += 1
                    if count >= 5:
                        break
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python debug_references_extraction.py <ruta_al_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"Error: El archivo {pdf_path} no existe")
        sys.exit(1)
    
    debug_pdf_references(pdf_path)

