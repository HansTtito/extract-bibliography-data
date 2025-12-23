"""
Handler para AWS Lambda - Export Function
Convierte FastAPI a formato compatible con Lambda usando Mangum
"""
import os
from mangum import Mangum
from app.main_export import app

# Mangum convierte FastAPI (ASGI) a formato compatible con Lambda
handler = Mangum(app, lifespan="off")

