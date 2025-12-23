"""
Script de prueba simple para extraer referencias de un PDF
Permite probar paso a paso sin afectar el código principal

Uso:
    python test_references_extraction_simple.py <ruta_al_pdf>
    
Ejemplo:
    python test_references_extraction_simple.py mi_archivo.pdf
"""
import sys
from pathlib import Path

# Agregar directorio raíz al path para imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.services.references_pdf_extractor import ReferencesPDFExtractor
    from app.services.reference_parser import ReferenceParser
except ImportError as e:
    print(f"❌ Error al importar módulos: {e}")
    print("Asegúrate de estar en el directorio raíz del proyecto")
    sys.exit(1)

def test_extraction(pdf_path: str, verbose: bool = True):
    """
    Prueba la extracción de referencias de un PDF
    
    Args:
        pdf_path: Ruta al archivo PDF
        verbose: Si True, muestra información detallada
    """
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"❌ Error: El archivo {pdf_path} no existe")
        return
    
    print(f"\n{'='*60}")
    print(f"📄 Probando extracción de referencias")
    print(f"Archivo: {pdf_file.name}")
    print(f"{'='*60}\n")
    
    # Leer PDF
    try:
        with open(pdf_file, 'rb') as f:
            pdf_content = f.read()
        print(f"✅ PDF leído: {len(pdf_content):,} bytes\n")
    except Exception as e:
        print(f"❌ Error al leer PDF: {e}")
        return
    
    # Extraer referencias
    extractor = ReferencesPDFExtractor()
    
    print("🔍 Extrayendo referencias del PDF...")
    print("-" * 60)
    
    try:
        references = extractor.extract_references(pdf_content)
        
        print(f"\n✅ Extracción completada")
        print(f"📊 Total de referencias encontradas: {len(references)}\n")
        
        if not references:
            print("⚠️  No se encontraron referencias")
            print("\nPosibles causas:")
            print("  - El PDF no tiene sección de referencias")
            print("  - El formato del PDF no es compatible")
            print("  - Las referencias están en formato no reconocido")
            return
        
        # Mostrar primeras referencias
        print(f"{'='*60}")
        print(f"📋 PRIMERAS 5 REFERENCIAS EXTRAÍDAS:")
        print(f"{'='*60}\n")
        
        for i, ref in enumerate(references[:5], 1):
            print(f"Referencia #{i}:")
            print(f"  Longitud: {len(ref)} caracteres")
            print(f"  Texto: {ref[:150]}...")
            print()
        
        if len(references) > 5:
            print(f"... y {len(references) - 5} referencias más\n")
        
        # Probar parsing de cada referencia
        print(f"{'='*60}")
        print(f"🔬 PROBANDO PARSING DE REFERENCIAS:")
        print(f"{'='*60}\n")
        
        parser = ReferenceParser()
        parsed_count = 0
        
        for i, ref in enumerate(references[:3], 1):  # Solo primeras 3 para no saturar
            print(f"\n--- Referencia #{i} ---")
            print(f"Texto original: {ref[:100]}...")
            
            try:
                parsed = parser.parse(ref)
                
                if parsed:
                    print(f"✅ Parseado exitosamente:")
                    print(f"  - Autores: {parsed.get('autores', 'N/A')}")
                    print(f"  - Año: {parsed.get('ano', 'N/A')}")
                    print(f"  - Título: {parsed.get('titulo_original', 'N/A')[:80]}...")
                    print(f"  - DOI: {parsed.get('doi', 'N/A')}")
                    print(f"  - Revista: {parsed.get('lugar_publicacion_entrega', 'N/A')}")
                    parsed_count += 1
                else:
                    print("⚠️  No se pudo parsear (campos vacíos)")
            except Exception as e:
                print(f"❌ Error al parsear: {e}")
        
        print(f"\n{'='*60}")
        print(f"📊 RESUMEN:")
        print(f"{'='*60}")
        print(f"Total referencias extraídas: {len(references)}")
        print(f"Referencias parseadas (muestra): {parsed_count}/3")
        print(f"{'='*60}\n")
        
        # Opción para guardar resultados
        save = input("¿Guardar resultados en archivo? (s/n): ").lower().strip()
        if save == 's':
            output_file = pdf_file.stem + "_referencias.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Referencias extraídas de: {pdf_file.name}\n")
                f.write(f"Total: {len(references)}\n")
                f.write("="*60 + "\n\n")
                for i, ref in enumerate(references, 1):
                    f.write(f"Referencia #{i}:\n")
                    f.write(f"{ref}\n")
                    f.write("-"*60 + "\n\n")
            print(f"✅ Resultados guardados en: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Error durante la extracción: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python test_references_extraction_simple.py <ruta_al_pdf>")
        print("\nEjemplo:")
        print("  python test_references_extraction_simple.py mi_archivo.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    test_extraction(pdf_path, verbose=True)

