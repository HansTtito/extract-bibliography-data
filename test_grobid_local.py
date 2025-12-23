#!/usr/bin/env python3
"""Script de prueba para GROBID local"""
import os
import sys

# Configurar GROBID
os.environ["USE_GROBID"] = "true"
os.environ["GROBID_URL"] = "http://localhost:8070"

from app.services.references_pdf_extractor import ReferencesPDFExtractor

def test_references_extraction(pdf_path: str):
    """Prueba extracción de referencias con GROBID"""
    print(f"\n{'='*60}")
    print(f"🧪 Probando extracción de referencias con GROBID")
    print(f"📄 PDF: {pdf_path}")
    print(f"{'='*60}\n")
    
    # Leer PDF
    with open(pdf_path, 'rb') as f:
        pdf_content = f.read()
    
    print(f"✅ PDF leído: {len(pdf_content)} bytes\n")
    
    # Extraer referencias
    extractor = ReferencesPDFExtractor()
    
    print(f"🔧 Configuración:")
    print(f"   - USE_GROBID: {extractor.grobid_service.use_grobid}")
    print(f"   - GROBID_URL: {extractor.grobid_service.grobid_url}\n")
    
    print(f"{'='*60}")
    print(f"🚀 Iniciando extracción...")
    print(f"{'='*60}\n")
    
    references = extractor.extract_references(pdf_content)
    
    print(f"\n{'='*60}")
    print(f"📊 RESULTADOS")
    print(f"{'='*60}")
    print(f"✅ Referencias extraídas: {len(references)}\n")
    
    if references:
        print(f"📋 Primeras {min(5, len(references))} referencias:\n")
        for i, ref in enumerate(references[:5], 1):
            print(f"  {i}. {ref[:150]}...")
            print()
    else:
        print(f"❌ No se encontraron referencias")
    
    return references

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python test_grobid_local.py <ruta_al_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"❌ Error: No se encontró el archivo: {pdf_path}")
        sys.exit(1)
    
    try:
        references = test_references_extraction(pdf_path)
        print(f"\n✅ Prueba completada exitosamente")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

