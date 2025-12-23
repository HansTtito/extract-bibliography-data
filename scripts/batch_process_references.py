#!/usr/bin/env python3
"""
Script batch para procesar referencias desde archivos de texto o PDFs
Uso: python batch_process_references.py <carpeta> [opciones]
"""

import sys
import os
import json
from pathlib import Path
from typing import List, Dict
from app.services.references_pdf_extractor import ReferencesPDFExtractor
from app.services.reference_parser import ReferenceParser
from app.services.crossref_service import CrossrefService
from app.database import SessionLocal, init_db
from app.models import Document


def process_reference_text(ref_text: str, parser: ReferenceParser, crossref_service: CrossrefService,
                           use_crossref: bool = True, save_to_db: bool = False) -> Dict:
    """Procesa una referencia en texto y retorna los datos"""
    try:
        # Parsear referencia
        parsed_data = parser.parse(ref_text)
        
        # Buscar en CrossRef si hay DOI
        if use_crossref and parsed_data.get("doi"):
            crossref_data = crossref_service.search_by_doi(parsed_data["doi"])
            if crossref_data:
                # Combinar: priorizar parsed para algunos campos, CrossRef para otros
                final_data = parsed_data.copy()
                
                # Enriquecer con CrossRef (solo si parsed no tiene el campo o está incompleto)
                for field in ["resumen_abstract", "keywords", "publicista_editorial"]:
                    if not final_data.get(field) and crossref_data.get(field):
                        final_data[field] = crossref_data[field]
                
                # Usar CrossRef para campos críticos si parsed está incompleto
                if not final_data.get("titulo_original") or len(final_data.get("titulo_original", "")) < 10:
                    if crossref_data.get("titulo_original"):
                        final_data["titulo_original"] = crossref_data["titulo_original"]
                
                parsed_data = final_data
        
        # Guardar en BD si se solicita
        if save_to_db:
            db = SessionLocal()
            try:
                # Obtener siguiente numero_doc
                last_doc = db.query(Document).order_by(Document.numero_doc.desc()).first()
                next_num = (last_doc.numero_doc + 1) if last_doc else 1
                
                # Crear documento
                doc = Document(
                    numero_doc=next_num,
                    autores=parsed_data.get("autores"),
                    ano=parsed_data.get("ano"),
                    titulo_original=parsed_data.get("titulo_original"),
                    keywords=parsed_data.get("keywords"),
                    resumen_abstract=parsed_data.get("resumen_abstract"),
                    lugar_publicacion_entrega=parsed_data.get("lugar_publicacion_entrega"),
                    publicista_editorial=parsed_data.get("publicista_editorial"),
                    volumen_edicion=parsed_data.get("volumen_edicion"),
                    isbn_issn=parsed_data.get("isbn_issn"),
                    paginas=parsed_data.get("paginas"),
                    doi=parsed_data.get("doi"),
                    link=parsed_data.get("link"),
                )
                
                db.add(doc)
                db.commit()
                parsed_data["numero_doc"] = next_num
                
            except Exception as e:
                db.rollback()
                print(f"   ⚠️  Error guardando en BD: {e}")
            finally:
                db.close()
        
        return {
            "status": "success",
            "original_text": ref_text[:200] + "..." if len(ref_text) > 200 else ref_text,
            "data": parsed_data
        }
        
    except Exception as e:
        return {
            "status": "error",
            "original_text": ref_text[:200] + "..." if len(ref_text) > 200 else ref_text,
            "error": str(e)
        }


def process_pdf_references(pdf_path: Path, extractor: ReferencesPDFExtractor, parser: ReferenceParser,
                          crossref_service: CrossrefService, use_crossref: bool = True, 
                          save_to_db: bool = False) -> List[Dict]:
    """Procesa un PDF con referencias"""
    print(f"\n📄 Procesando PDF: {pdf_path.name}")
    
    try:
        # Leer PDF
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        # Extraer referencias
        print(f"   🔍 Extrayendo referencias...")
        references = extractor.extract_references(pdf_content)
        
        if not references:
            print(f"   ⚠️  No se encontraron referencias")
            return []
        
        print(f"   ✅ {len(references)} referencias encontradas")
        
        # Procesar cada referencia
        results = []
        for i, ref_text in enumerate(references, 1):
            print(f"   [{i}/{len(references)}] Procesando referencia...", end="\r")
            result = process_reference_text(ref_text, parser, crossref_service, use_crossref, save_to_db)
            result["reference_number"] = i
            results.append(result)
        
        print(f"   ✅ {len(references)} referencias procesadas")
        return results
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return [{
            "status": "error",
            "file": pdf_path.name,
            "error": str(e)
        }]


def process_text_file(txt_path: Path, parser: ReferenceParser, crossref_service: CrossrefService,
                      use_crossref: bool = True, save_to_db: bool = False) -> List[Dict]:
    """Procesa un archivo de texto con referencias (una por línea)"""
    print(f"\n📄 Procesando archivo: {txt_path.name}")
    
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Filtrar líneas vacías
        references = [line.strip() for line in lines if line.strip()]
        
        if not references:
            print(f"   ⚠️  Archivo vacío")
            return []
        
        print(f"   ✅ {len(references)} referencias encontradas")
        
        # Procesar cada referencia
        results = []
        for i, ref_text in enumerate(references, 1):
            print(f"   [{i}/{len(references)}] Procesando...", end="\r")
            result = process_reference_text(ref_text, parser, crossref_service, use_crossref, save_to_db)
            result["reference_number"] = i
            results.append(result)
        
        print(f"   ✅ {len(references)} referencias procesadas")
        return results
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return [{
            "status": "error",
            "file": txt_path.name,
            "error": str(e)
        }]


def main():
    if len(sys.argv) < 2:
        print("""
Uso: python batch_process_references.py <carpeta_o_archivo> [opciones]

El script procesa:
  - PDFs: Extrae referencias de PDFs
  - Archivos .txt: Procesa referencias (una por línea)

Opciones:
  --no-crossref      No buscar en CrossRef
  --save-db           Guardar resultados en base de datos
  --output JSON       Archivo de salida JSON (default: referencias_resultados.json)
  --output-dir DIR    Carpeta de salida (default: resultados/)

Ejemplos:
  python batch_process_references.py ./referencias
  python batch_process_references.py ./referencias --save-db
  python batch_process_references.py ./referencias/referencias.txt --save-db
  python batch_process_references.py ./pdfs --no-crossref
        """)
        return 1
    
    # Parsear argumentos
    input_path = Path(sys.argv[1])
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
    output_file = output_dir / "referencias_resultados.json"
    if "--output" in sys.argv:
        try:
            idx = sys.argv.index("--output")
            output_file = Path(sys.argv[idx + 1])
        except (IndexError, ValueError):
            pass
    
    if not input_path.exists():
        print(f"❌ Error: '{input_path}' no existe")
        return 1
    
    # Inicializar servicios
    extractor = ReferencesPDFExtractor()
    parser = ReferenceParser()
    crossref_service = CrossrefService() if use_crossref else None
    
    # Inicializar BD si se va a guardar
    if save_to_db:
        init_db()
    
    # Procesar según tipo
    all_results = []
    
    if input_path.is_file():
        # Es un archivo
        if input_path.suffix.lower() == '.pdf':
            results = process_pdf_references(input_path, extractor, parser, crossref_service, 
                                           use_crossref, save_to_db)
            all_results.extend(results)
        elif input_path.suffix.lower() == '.txt':
            results = process_text_file(input_path, parser, crossref_service, use_crossref, save_to_db)
            all_results.extend(results)
        else:
            print(f"❌ Error: Formato no soportado. Use .pdf o .txt")
            return 1
    
    elif input_path.is_dir():
        # Es una carpeta
        pdf_files = list(input_path.glob("*.pdf"))
        txt_files = list(input_path.glob("*.txt"))
        
        if not pdf_files and not txt_files:
            print(f"❌ No se encontraron archivos .pdf o .txt en '{input_path}'")
            return 1
        
        print(f"📁 Carpeta: {input_path}")
        print(f"📄 PDFs encontrados: {len(pdf_files)}")
        print(f"📄 Archivos .txt encontrados: {len(txt_files)}")
        print(f"🌐 CrossRef: {'Sí' if use_crossref else 'No'}")
        print(f"💾 Guardar en BD: {'Sí' if save_to_db else 'No'}")
        print("="*60)
        
        # Procesar PDFs
        for pdf_file in pdf_files:
            results = process_pdf_references(pdf_file, extractor, parser, crossref_service, 
                                           use_crossref, save_to_db)
            for r in results:
                r["source_file"] = pdf_file.name
            all_results.extend(results)
        
        # Procesar archivos de texto
        for txt_file in txt_files:
            results = process_text_file(txt_file, parser, crossref_service, use_crossref, save_to_db)
            for r in results:
                r["source_file"] = txt_file.name
            all_results.extend(results)
    
    # Estadísticas
    success_count = sum(1 for r in all_results if r.get("status") == "success")
    error_count = len(all_results) - success_count
    
    # Guardar resultados
    output_data = {
        "total": len(all_results),
        "success": success_count,
        "errors": error_count,
        "results": all_results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN")
    print("="*60)
    print(f"Total procesadas: {len(all_results)}")
    print(f"✅ Exitosas: {success_count}")
    print(f"❌ Errores: {error_count}")
    print(f"💾 Resultados guardados en: {output_file}")
    
    if save_to_db:
        print(f"💾 Documentos guardados en base de datos")
    
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

