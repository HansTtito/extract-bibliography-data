#!/usr/bin/env python3
"""
Script para iniciar el servidor de la plataforma
"""
import uvicorn

if __name__ == "__main__":
    import os
    
    # En la nube, usar el puerto proporcionado por la plataforma
    port = int(os.getenv("PORT", 8001))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=reload
    )

