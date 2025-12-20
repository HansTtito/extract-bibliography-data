#!/usr/bin/env python3
"""
Script de prueba para parsear una referencia bibliográfica en texto
Uso: python test_reference_parser.py "<texto de referencia>"
"""

import sys
import json
from app.services.reference_parser import ReferenceParser
from app.services.crossref_service import CrossrefService


def print_parsed_data(data, title="Información Parseada"):
    """Imprime datos parseados de forma legible"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)
    
    if not data:
        print("❌ No se pudo parsear información")
        return
    
    fields = {
        "Autores": data.get("autores"),
        "Año": data.get("ano"),
        "Título": data.get("titulo_original"),
        "DOI": data.get("doi"),
        "Revista/Lugar": data.get("lugar_publicacion_entrega"),
        "Editorial": data.get("publicista_editorial"),
        "Volumen": data.get("volumen_edicion"),
        "Páginas": data.get("paginas"),
        "ISBN/ISSN": data.get("isbn_issn"),
        "Tipo Documento": data.get("tipo_documento"),
    }
    
    found_any = False
    for field_name, value in fields.items():
        if value:
            found_any = True
            print(f"\n📄 {field_name}:")
            print(f"   {value}")
    
    if not found_any:
        print("\n⚠️  No se extrajo información estructurada")
    
    print("\n" + "="*60)


def main():
    if len(sys.argv) < 2:
        print("""
Uso: python test_reference_parser.py "<texto de referencia>" [--with-crossref]

Opciones:
  --with-crossref    También buscar información en CrossRef si hay DOI

Ejemplos:
  python test_reference_parser.py "Smith, J., 2020. Title of paper. Journal Name, 10, 123-145."
  python test_reference_parser.py "Smith, J., 2020. Title of paper. Journal Name, 10, 123-145." --with-crossref
        """)
        return
    
    reference_text = sys.argv[1]
    use_crossref = "--with-crossref" in sys.argv
    
    print(f"📝 Referencia a parsear:")
    print(f"   {reference_text}")
    
    try:
        # Parsear referencia
        print("\n🔍 Parseando referencia...")
        parser = ReferenceParser()
        parsed_data = parser.parse(reference_text)
        
        # Mostrar resultados
        print_parsed_data(parsed_data, "Información Parseada")
        
        # Si se solicita, buscar en CrossRef
        if use_crossref:
            doi = parsed_data.get("doi")
            if doi:
                print(f"\n🌐 Buscando en CrossRef con DOI: {doi}")
                crossref_service = CrossrefService()
                crossref_data = crossref_service.search_by_doi(doi)
                
                if crossref_data:
                    print_parsed_data(crossref_data, "Información de CrossRef")
                    
                    # Comparar
                    print("\n" + "="*60)
                    print("  Comparación: Parseado vs CrossRef")
                    print("="*60)
                    
                    comparison_fields = ["autores", "titulo_original", "ano", "lugar_publicacion_entrega"]
                    for field in comparison_fields:
                        parsed_val = parsed_data.get(field)
                        crossref_val = crossref_data.get(field)
                        if parsed_val or crossref_val:
                            print(f"\n{field}:")
                            print(f"  Parseado:  {parsed_val or '(no encontrado)'}")
                            print(f"  CrossRef:  {crossref_val or '(no encontrado)'}")
                else:
                    print("⚠️  No se encontró información en CrossRef")
            else:
                print("⚠️  No hay DOI para buscar en CrossRef")
        
        # Guardar en JSON
        output = {
            "original_text": reference_text,
            "parsed": parsed_data
        }
        
        print(f"\n💾 Resultado JSON:")
        print(json.dumps(output, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

