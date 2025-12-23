"""
Handler para AWS Lambda
Convierte FastAPI a formato compatible con Lambda usando Mangum
"""
import os
from mangum import Mangum
from app.main import app
from app.database import init_db

# Inicializar base de datos al cargar el módulo (una vez por container)
# Esto crea las tablas si no existen
try:
    init_db()
    print("✅ Base de datos inicializada correctamente")
except Exception as e:
    print(f"⚠️ Error inicializando base de datos: {e}")

# Mangum convierte FastAPI (ASGI) a formato compatible con Lambda
# lifespan="off" porque Lambda maneja el ciclo de vida
handler = Mangum(app, lifespan="off")

