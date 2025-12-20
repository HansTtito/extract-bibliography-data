#!/usr/bin/env python3
"""
Script para limpiar la base de datos
Opciones:
1. Eliminar todos los registros (mantener tablas)
2. Eliminar y recrear todas las tablas
3. Solo resetear contador de numero_doc
"""

import sys
from sqlalchemy import text
from app.database import engine, Base, SessionLocal
from app.models import Document


def clear_all_data():
    """Elimina todos los registros pero mantiene las tablas"""
    db = SessionLocal()
    try:
        print("🗑️  Eliminando todos los registros...")
        deleted = db.query(Document).delete()
        db.commit()
        print(f"✅ Eliminados {deleted} documentos")
        return deleted
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        return 0
    finally:
        db.close()


def drop_and_recreate_tables():
    """Elimina todas las tablas y las recrea"""
    try:
        print("🗑️  Eliminando todas las tablas...")
        Base.metadata.drop_all(bind=engine)
        print("✅ Tablas eliminadas")
        
        print("🔨 Recreando tablas...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas recreadas")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def reset_sequence():
    """Resetea el contador de numero_doc"""
    db = SessionLocal()
    try:
        print("🔄 Reseteando secuencia de numero_doc...")
        # Obtener el máximo numero_doc actual
        max_num = db.query(Document.numero_doc).order_by(Document.numero_doc.desc()).first()
        if max_num and max_num[0]:
            # Resetear la secuencia al siguiente número después del máximo
            next_val = max_num[0] + 1
            db.execute(text(f"SELECT setval('documents_numero_doc_seq', {next_val}, false)"))
        else:
            # Si no hay registros, resetear a 1
            db.execute(text("SELECT setval('documents_numero_doc_seq', 1, false)"))
        db.commit()
        print("✅ Secuencia reseteada")
        return True
    except Exception as e:
        db.rollback()
        # Si la secuencia no existe, no es problema (SQLAlchemy maneja autoincrement)
        print(f"⚠️  No se pudo resetear secuencia (puede ser normal): {e}")
        return False
    finally:
        db.close()


def show_stats():
    """Muestra estadísticas de la base de datos"""
    db = SessionLocal()
    try:
        count = db.query(Document).count()
        print(f"\n📊 Estadísticas:")
        print(f"   Total de documentos: {count}")
        
        if count > 0:
            max_num = db.query(Document.numero_doc).order_by(Document.numero_doc.desc()).first()
            min_num = db.query(Document.numero_doc).order_by(Document.numero_doc.asc()).first()
            print(f"   numero_doc mínimo: {min_num[0] if min_num else 'N/A'}")
            print(f"   numero_doc máximo: {max_num[0] if max_num else 'N/A'}")
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
    finally:
        db.close()


def main():
    """Función principal"""
    if len(sys.argv) < 2:
        print("""
Uso: python clear_database.py [opción]

Opciones:
  clear       - Elimina todos los registros (mantiene tablas)
  recreate    - Elimina y recrea todas las tablas
  reset       - Solo resetea el contador de numero_doc
  stats       - Muestra estadísticas de la base de datos
  all         - Elimina registros Y resetea contador

Ejemplos:
  python clear_database.py clear
  python clear_database.py recreate
  python clear_database.py stats
        """)
        return
    
    option = sys.argv[1].lower()
    
    # Mostrar estadísticas antes
    show_stats()
    
    if option == "clear":
        print("\n⚠️  ¿Estás seguro de que quieres eliminar TODOS los registros? (s/N): ", end="")
        confirm = input().strip().lower()
        if confirm == 's' or confirm == 'y' or confirm == 'si' or confirm == 'yes':
            clear_all_data()
            reset_sequence()
        else:
            print("❌ Operación cancelada")
    
    elif option == "recreate":
        print("\n⚠️  ¿Estás seguro de que quieres ELIMINAR Y RECREAR todas las tablas? (s/N): ", end="")
        confirm = input().strip().lower()
        if confirm == 's' or confirm == 'y' or confirm == 'si' or confirm == 'yes':
            drop_and_recreate_tables()
        else:
            print("❌ Operación cancelada")
    
    elif option == "reset":
        reset_sequence()
    
    elif option == "stats":
        pass  # Ya se mostró arriba
    
    elif option == "all":
        print("\n⚠️  ¿Estás seguro de que quieres eliminar TODOS los registros? (s/N): ", end="")
        confirm = input().strip().lower()
        if confirm == 's' or confirm == 'y' or confirm == 'si' or confirm == 'yes':
            clear_all_data()
            reset_sequence()
        else:
            print("❌ Operación cancelada")
    
    else:
        print(f"❌ Opción desconocida: {option}")
        print("Usa: clear, recreate, reset, stats, o all")
        return
    
    # Mostrar estadísticas después
    print()
    show_stats()


if __name__ == "__main__":
    main()

