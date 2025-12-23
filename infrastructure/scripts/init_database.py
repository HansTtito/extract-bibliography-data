"""
Script para inicializar la base de datos en RDS
Crea todas las tablas definidas en los modelos
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.database import engine, Base
from app.models import Document

def init_database():
    """Crea todas las tablas en la base de datos"""
    print("Inicializando base de datos...")
    print(f"Conectando a: {os.getenv('DATABASE_URL', 'No configurado')}")
    
    try:
        # Crear todas las tablas
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas creadas exitosamente!")
        
        # Verificar tablas creadas
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\nTablas en la base de datos: {tables}")
        
    except Exception as e:
        print(f"❌ Error inicializando base de datos: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_database()

