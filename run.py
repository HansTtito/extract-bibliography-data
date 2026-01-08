#!/usr/bin/env python3
"""
Script para iniciar el servidor de la plataforma
"""
import uvicorn

if __name__ == "__main__":
    import os
    
    # Configurar GROBID para desarrollo local
    if not os.getenv("DATABASE_URL"):
        os.environ.setdefault("USE_GROBID", "true")
        os.environ.setdefault("GROBID_URL", "http://localhost:8070")
        os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/bibliografia")
        print("Configuracion local activada (GROBID + PostgreSQL local)")
    
    # En la nube, usar el puerto proporcionado por la plataforma
    port = int(os.getenv("PORT", 8001))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=reload
    )

