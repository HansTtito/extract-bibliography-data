#!/usr/bin/env python3
"""
Script de prueba para extraer referencias bibliográficas de un PDF
Uso: python test_references_extraction.py <ruta_al_pdf>
"""

import sys
import json
from pathlib import Path
from app.services.references_pdf_extractor import ReferencesPDFExtractor
from app.services.reference_parser import ReferenceParser


def print_reference(ref_text, index, total):
    """Imprime una referencia de forma legible"""
    print(f"\n{'='*60}")
    print(f"  Referencia {index + 1} de {total}")
    print(f"{'='*60}")
    print(f"\n{ref_text}")
    print(f"\n{'-'*60}")


def print_parsed_info(parsed_data, index):
    """Imprime información parseada de una referencia"""
    if not parsed_data:
        print("⚠️  No se pudo parsear información estructurada")
        return
    
    print(f"\n📋 Información Extraída (Referencia {index + 1}):")
    print("-" * 60)
    
    fields = {
        "Autores": parsed_data.get("autores"),
        "Año": parsed_data.get("ano"),
        "Título": parsed_data.get("titulo_original"),
        "DOI": parsed_data.get("doi"),
        "Revista/Lugar": parsed_data.get("lugar_publicacion_entrega"),
        "Editorial": parsed_data.get("publicista_editorial"),
        "Volumen": parsed_data.get("volumen_edicion"),
        "Páginas": parsed_data.get("paginas"),
        "ISBN/ISSN": parsed_data.get("isbn_issn"),
    }
    
    found_any = False
    for field_name, value in fields.items():
        if value:
            found_any = True
            print(f"  • {field_name}: {value}")
    
    if not found_any:
        print("  (No se extrajo información estructurada)")


def main():
    if len(sys.argv) < 2:
        print("""
Uso: python test_references_extraction.py <ruta_al_pdf> [opciones]

Opciones:
  --parse          También parsear cada referencia extraída
  --save           Guardar referencias en archivo JSON
  --limit N        Limitar a las primeras N referencias

Ejemplos:
  python test_references_extraction.py referencias.pdf
  python test_references_extraction.py referencias.pdf --parse
  python test_references_extraction.py referencias.pdf --parse --save
  python test_references_extraction.py referencias.pdf --limit 5
        """)
        return
    
    pdf_path = Path(sys.argv[1])
    should_parse = "--parse" in sys.argv
    should_save = "--save" in sys.argv
    
    # Obtener límite si existe
    limit = None
    if "--limit" in sys.argv:
        try:
            limit_idx = sys.argv.index("--limit")
            limit = int(sys.argv[limit_idx + 1])
        except (ValueError, IndexError):
            print("⚠️  --limit requiere un número, ignorando...")
    
    if not pdf_path.exists():
        print(f"❌ Error: El archivo '{pdf_path}' no existe")
        return
    
    if not pdf_path.suffix.lower() == '.pdf':
        print(f"❌ Error: El archivo debe ser un PDF")
        return
    
    print(f"📖 Procesando: {pdf_path.name}")
    print(f"📏 Tamaño: {pdf_path.stat().st_size / 1024:.2f} KB")
    
    try:
        # Leer PDF
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        # Extraer referencias
        print("\n🔍 Extrayendo referencias del PDF...")
        extractor = ReferencesPDFExtractor()
        references = extractor.extract_references(pdf_content)
        
        if not references:
            print("\n❌ No se encontraron referencias en el PDF")
            print("   Verifica que el PDF tenga una sección de referencias")
            return 1
        
        # Aplicar límite si se especificó
        if limit:
            references = references[:limit]
            print(f"\n⚠️  Mostrando solo las primeras {limit} referencias")
        
        total = len(references)
        print(f"\n✅ Se encontraron {total} referencias")
        
        # Mostrar referencias
        parser = ReferenceParser() if should_parse else None
        results = []
        
        for i, ref_text in enumerate(references):
            print_reference(ref_text, i, total)
            
            # Parsear si se solicita
            if should_parse and parser:
                parsed = parser.parse(ref_text)
                print_parsed_info(parsed, i)
                results.append({
                    "text": ref_text,
                    "parsed": parsed
                })
            else:
                results.append({
                    "text": ref_text,
                    "parsed": None
                })
        
        # Guardar si se solicita
        if should_save:
            output_file = pdf_path.stem + "_references.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "total": total,
                    "references": results
                }, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Resultados guardados en: {output_file}")
        
        print(f"\n{'='*60}")
        print(f"✅ Proceso completado: {total} referencias extraídas")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n❌ Error procesando PDF: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

