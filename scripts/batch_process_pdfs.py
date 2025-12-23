#!/usr/bin/env python3
"""
Script batch para procesar múltiples PDFs desde una carpeta
Uso: python batch_process_pdfs.py <carpeta_pdfs> [opciones]
"""

import sys
import os
import json
from pathlib import Path
from typing import List, Dict
from app.services.pdf_extractor import PDFExtractor
from app.services.crossref_service import CrossrefService
from app.database import SessionLocal, init_db
from app.models import Document


def process_pdf(pdf_path: Path, extractor: PDFExtractor, crossref_service: CrossrefService, 
              use_crossref: bool = True, save_to_db: bool = False) -> Dict:
    """Procesa un PDF y retorna los datos extraídos"""
    print(f"\n📄 Procesando: {pdf_path.name}")
    
    try:
        # Leer PDF
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        # Extraer información
        extracted_data = extractor.extract(pdf_content)
        
        # Buscar en CrossRef si hay DOI
        if use_crossref and extracted_data.get("doi"):
            print(f"   🌐 Buscando en CrossRef (DOI: {extracted_data['doi']})...")
            crossref_data = crossref_service.search_by_doi(extracted_data["doi"])
            
            if crossref_data:
                # Combinar datos: priorizar CrossRef para campos críticos
                final_data = {}
                
                # Campos críticos de CrossRef (más confiables)
                critical_fields = ["autores", "titulo_original", "ano", "lugar_publicacion_entrega", 
                                  "publicista_editorial", "volumen_edicion", "isbn_issn", "doi", "link"]
                for field in critical_fields:
                    final_data[field] = crossref_data.get(field) or extracted_data.get(field)
                
                # Otros campos del PDF (abstract, keywords)
                final_data["resumen_abstract"] = crossref_data.get("resumen_abstract") or extracted_data.get("resumen_abstract")
                final_data["keywords"] = crossref_data.get("keywords") or extracted_data.get("keywords")
                final_data["paginas"] = extracted_data.get("paginas")
                
                extracted_data = final_data
                print(f"   ✅ Datos enriquecidos con CrossRef")
        
        # Guardar en base de datos si se solicita
        if save_to_db:
            db = SessionLocal()
            try:
                # Obtener siguiente numero_doc
                last_doc = db.query(Document).order_by(Document.numero_doc.desc()).first()
                next_num = (last_doc.numero_doc + 1) if last_doc else 1
                
                # Crear documento
                doc = Document(
                    numero_doc=next_num,
                    autores=extracted_data.get("autores"),
                    ano=extracted_data.get("ano"),
                    titulo_original=extracted_data.get("titulo_original"),
                    keywords=extracted_data.get("keywords"),
                    resumen_abstract=extracted_data.get("resumen_abstract"),
                    lugar_publicacion_entrega=extracted_data.get("lugar_publicacion_entrega"),
                    publicista_editorial=extracted_data.get("publicista_editorial"),
                    volumen_edicion=extracted_data.get("volumen_edicion"),
                    isbn_issn=extracted_data.get("isbn_issn"),
                    paginas=extracted_data.get("paginas"),
                    doi=extracted_data.get("doi"),
                    link=extracted_data.get("link"),
                )
                
                db.add(doc)
                db.commit()
                print(f"   💾 Guardado en BD como documento #{next_num}")
                
            except Exception as e:
                db.rollback()
                print(f"   ⚠️  Error guardando en BD: {e}")
            finally:
                db.close()
        
        return {
            "file": pdf_path.name,
            "status": "success",
            "data": extracted_data
        }
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {
            "file": pdf_path.name,
            "status": "error",
            "error": str(e)
        }


def main():
    if len(sys.argv) < 2:
        print("""
Uso: python batch_process_pdfs.py <carpeta_pdfs> [opciones]

Opciones:
  --no-crossref      No buscar en CrossRef
  --save-db          Guardar resultados en base de datos
  --output JSON      Guardar resultados en archivo JSON (default: resultados.json)
  --output-dir DIR   Carpeta donde guardar resultados (default: resultados/)

Ejemplos:
  python batch_process_pdfs.py ./pdfs
  python batch_process_pdfs.py ./pdfs --save-db
  python batch_process_pdfs.py ./pdfs --no-crossref --output resultados.json
  python batch_process_pdfs.py ./pdfs --save-db --output-dir ./resultados
        """)
        return 1
    
    # Parsear argumentos
    folder_path = Path(sys.argv[1])
    use_crossref = "--no-crossref" not in sys.argv
    save_to_db = "--save-db" in sys.argv
    
    # Obtener carpeta de salida
    output_dir = Path("resultados")
    if "--output-dir" in sys.argv:
        try:
            idx = sys.argv.index("--output-dir")
            output_dir = Path(sys.argv[idx + 1])
        except (IndexError, ValueError):
            pass
    
    output_dir.mkdir(exist_ok=True)
    
    # Obtener archivo de salida
    output_file = output_dir / "resultados.json"
    if "--output" in sys.argv:
        try:
            idx = sys.argv.index("--output")
            output_file = Path(sys.argv[idx + 1])
        except (IndexError, ValueError):
            pass
    
    if not folder_path.exists():
        print(f"❌ Error: La carpeta '{folder_path}' no existe")
        return 1
    
    if not folder_path.is_dir():
        print(f"❌ Error: '{folder_path}' no es una carpeta")
        return 1
    
    # Buscar PDFs
    pdf_files = list(folder_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No se encontraron archivos PDF en '{folder_path}'")
        return 1
    
    print(f"📁 Carpeta: {folder_path}")
    print(f"📄 PDFs encontrados: {len(pdf_files)}")
    print(f"🌐 CrossRef: {'Sí' if use_crossref else 'No'}")
    print(f"💾 Guardar en BD: {'Sí' if save_to_db else 'No'}")
    print(f"📤 Salida: {output_file}")
    print("="*60)
    
    # Inicializar servicios
    extractor = PDFExtractor()
    crossref_service = CrossrefService() if use_crossref else None
    
    # Inicializar BD si se va a guardar
    if save_to_db:
        init_db()
    
    # Procesar cada PDF
    results = []
    success_count = 0
    error_count = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] ", end="")
        result = process_pdf(pdf_file, extractor, crossref_service, use_crossref, save_to_db)
        results.append(result)
        
        if result["status"] == "success":
            success_count += 1
        else:
            error_count += 1
    
    # Guardar resultados
    output_data = {
        "total": len(pdf_files),
        "success": success_count,
        "errors": error_count,
        "results": results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN")
    print("="*60)
    print(f"Total procesados: {len(pdf_files)}")
    print(f"✅ Exitosos: {success_count}")
    print(f"❌ Errores: {error_count}")
    print(f"💾 Resultados guardados en: {output_file}")
    
    if save_to_db:
        print(f"💾 Documentos guardados en base de datos")
    
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

