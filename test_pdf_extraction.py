#!/usr/bin/env python3
"""
Script de prueba para extraer información bibliográfica de un PDF
Uso: python test_pdf_extraction.py <ruta_al_pdf>
"""

import sys
import json
from pathlib import Path
from app.services.pdf_extractor import PDFExtractor
from app.services.crossref_service import CrossrefService


def print_results(data, title="Resultados de Extracción"):
    """Imprime los resultados de forma legible"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)
    
    if not data:
        print("❌ No se extrajo información")
        return
    
    # Campos principales
    fields = {
        "Autores": data.get("autores"),
        "Año": data.get("ano"),
        "Título": data.get("titulo_original"),
        "DOI": data.get("doi"),
        "ISBN/ISSN": data.get("isbn_issn"),
        "Revista/Lugar": data.get("lugar_publicacion_entrega"),
        "Editorial": data.get("publicista_editorial"),
        "Volumen": data.get("volumen_edicion"),
        "Páginas": data.get("paginas"),
        "Keywords": data.get("keywords"),
        "Resumen": data.get("resumen_abstract"),
    }
    
    for field_name, value in fields.items():
        if value:
            print(f"\n📄 {field_name}:")
            # Truncar si es muy largo
            if isinstance(value, str) and len(value) > 200:
                print(f"   {value[:200]}...")
            else:
                print(f"   {value}")
    
    print("\n" + "="*60)


def main():
    if len(sys.argv) < 2:
        print("""
Uso: python test_pdf_extraction.py <ruta_al_pdf> [--with-crossref]

Opciones:
  --with-crossref    También buscar información en CrossRef si hay DOI

Ejemplos:
  python test_pdf_extraction.py documento.pdf
  python test_pdf_extraction.py documento.pdf --with-crossref
        """)
        return
    
    pdf_path = Path(sys.argv[1])
    use_crossref = "--with-crossref" in sys.argv
    
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
        
        # Extraer información
        print("\n🔍 Extrayendo información del PDF...")
        extractor = PDFExtractor()
        extracted_data = extractor.extract(pdf_content)
        
        # Mostrar resultados iniciales
        print_results(extracted_data, "Extracción del PDF")
        
        # Si hay DOI y se solicita, buscar en CrossRef
        if use_crossref and extracted_data.get("doi"):
            print("\n🌐 Buscando información adicional en CrossRef...")
            crossref_service = CrossrefService()
            crossref_data = crossref_service.search_by_doi(extracted_data["doi"])
            
            if crossref_data:
                print_results(crossref_data, "Información de CrossRef")
                
                # Comparar datos
                print("\n" + "="*60)
                print("  Comparación: PDF vs CrossRef")
                print("="*60)
                
                comparison_fields = ["autores", "titulo_original", "ano", "lugar_publicacion_entrega"]
                for field in comparison_fields:
                    pdf_val = extracted_data.get(field)
                    crossref_val = crossref_data.get(field)
                    if pdf_val or crossref_val:
                        print(f"\n{field}:")
                        print(f"  PDF:      {pdf_val or '(no encontrado)'}")
                        print(f"  CrossRef: {crossref_val or '(no encontrado)'}")
        
        # Guardar resultados en JSON (opcional)
        output_file = pdf_path.stem + "_extracted.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Resultados guardados en: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Error procesando PDF: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

