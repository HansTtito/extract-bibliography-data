"""
Handler para AWS Lambda
Convierte FastAPI a formato compatible con Lambda usando Mangum
"""
import os
from mangum import Mangum
from app.main import app

# Configurar variables de entorno si no están definidas
# Lambda las pasará desde la configuración de la función
if not os.getenv("DATABASE_URL"):
    # Esto debería venir de las variables de entorno de Lambda
    pass

# Mangum convierte FastAPI (ASGI) a formato compatible con Lambda
# lifespan="off" porque Lambda maneja el ciclo de vida
handler = Mangum(app, lifespan="off")

