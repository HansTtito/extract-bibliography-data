"""
Script de prueba DETALLADO para extraer referencias de un PDF
Muestra paso a paso qué está haciendo el extractor

Uso:
    python test_references_detailed.py <ruta_al_pdf>
"""
import sys
from pathlib import Path
import re

# Agregar directorio raíz al path para imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.services.references_pdf_extractor import ReferencesPDFExtractor
    from app.services.reference_parser import ReferenceParser
    from app.utils.patterns import BiblioPatterns
except ImportError as e:
    print(f"❌ Error al importar módulos: {e}")
    sys.exit(1)


def print_section(title: str, char: str = "="):
    """Imprime una sección con formato"""
    print(f"\n{char*60}")
    print(f"{title}")
    print(f"{char*60}\n")


def test_detailed(pdf_path: str):
    """Prueba detallada paso a paso"""
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"❌ Error: El archivo {pdf_path} no existe")
        return
    
    print_section(f"📄 PRUEBA DETALLADA: {pdf_file.name}")
    
    # PASO 1: Leer PDF
    print("🔹 PASO 1: Leyendo PDF...")
    try:
        with open(pdf_file, 'rb') as f:
            pdf_content = f.read()
        print(f"   ✅ PDF leído: {len(pdf_content):,} bytes")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # PASO 2: Extraer texto del PDF
    print("\n🔹 PASO 2: Extrayendo texto del PDF...")
    import pdfplumber
    from io import BytesIO
    
    try:
        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            pages_text = []
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                pages_text.append(page_text)
                print(f"   📄 Página {i+1}: {len(page_text)} caracteres")
            
            full_text = '\n'.join(pages_text)
            print(f"   ✅ Texto total: {len(full_text):,} caracteres")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # PASO 3: Buscar sección de referencias
    print("\n🔹 PASO 3: Buscando sección de referencias...")
    
    # Normalizar texto
    from app.utils.text_processing import normalize_text_spacing
    normalized_text = normalize_text_spacing(full_text)
    print(f"   📝 Texto normalizado: {len(normalized_text):,} caracteres")
    
    # Buscar patrones de sección
    ref_patterns = [
        r'REFERENCES\s*\n',
        r'References\s*\n',
        r'LITERATURE\s+CITED\s*\n',
        r'Bibliography\s*\n',
        r'REFERENCIAS\s*\n',
    ]
    
    ref_section_found = False
    for pattern in ref_patterns:
        match = re.search(pattern, normalized_text, re.IGNORECASE | re.MULTILINE)
        if match:
            print(f"   ✅ Sección encontrada con patrón: {pattern}")
            print(f"   📍 Posición: {match.start()}-{match.end()}")
            ref_section_found = True
            break
    
    if not ref_section_found:
        print("   ⚠️  No se encontró sección explícita, usando últimas páginas")
    
    # PASO 4: Extraer referencias
    print("\n🔹 PASO 4: Extrayendo referencias individuales...")
    extractor = ReferencesPDFExtractor()
    
    try:
        references = extractor.extract_references(pdf_content)
        print(f"   ✅ Referencias extraídas: {len(references)}")
        
        if references:
            print(f"\n   📋 Muestra de referencias:")
            for i, ref in enumerate(references[:3], 1):
                print(f"\n   Referencia #{i}:")
                print(f"      Longitud: {len(ref)} caracteres")
                print(f"      Primeros 100 chars: {ref[:100]}...")
                
                # Verificar patrones
                has_year = bool(re.search(BiblioPatterns.YEAR_FULL, ref))
                has_author = bool(re.match(BiblioPatterns.AUTHOR_FULL, ref))
                print(f"      Tiene año: {'✅' if has_year else '❌'}")
                print(f"      Empieza con autor: {'✅' if has_author else '❌'}")
        else:
            print("   ⚠️  No se encontraron referencias")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # PASO 5: Parsear referencias
    if references:
        print("\n🔹 PASO 5: Parseando referencias...")
        parser = ReferenceParser()
        
        parsed_results = []
        for i, ref in enumerate(references[:5], 1):  # Solo primeras 5
            print(f"\n   📝 Parseando referencia #{i}...")
            try:
                parsed = parser.parse(ref)
                if parsed and any(parsed.values()):
                    print(f"      ✅ Parseado:")
                    print(f"         - Autores: {parsed.get('autores', 'N/A')}")
                    print(f"         - Año: {parsed.get('ano', 'N/A')}")
                    print(f"         - Título: {str(parsed.get('titulo_original', 'N/A'))[:60]}...")
                    print(f"         - DOI: {parsed.get('doi', 'N/A')}")
                    parsed_results.append(parsed)
                else:
                    print(f"      ⚠️  Campos vacíos")
            except Exception as e:
                print(f"      ❌ Error: {e}")
        
        print_section("📊 RESUMEN FINAL")
        print(f"Total referencias extraídas: {len(references)}")
        print(f"Referencias parseadas (muestra): {len(parsed_results)}/5")
        
        if parsed_results:
            print(f"\n✅ ¡Prueba exitosa! El extractor está funcionando.")
        else:
            print(f"\n⚠️  Se extrajeron referencias pero no se pudieron parsear.")
            print(f"   Esto puede indicar que el formato de las referencias")
            print(f"   no coincide con los patrones esperados.")
    else:
        print_section("⚠️  NO SE ENCONTRARON REFERENCIAS")
        print("Posibles causas:")
        print("  1. El PDF no tiene sección de referencias")
        print("  2. El formato del PDF no es compatible")
        print("  3. Las referencias están en formato no reconocido")
        print("\nSugerencias:")
        print("  - Verifica que el PDF tenga una sección 'REFERENCES'")
        print("  - Intenta con otro PDF para comparar")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python test_references_detailed.py <ruta_al_pdf>")
        print("\nEjemplo:")
        print("  python test_references_detailed.py mi_archivo.pdf")
        sys.exit(1)
    
    test_detailed(sys.argv[1])

