from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import download
import os

app = FastAPI(
    title="Plataforma de Extracción Bibliográfica - Exports",
    description="API para exportar datos en CSV/Excel/JSON",
    version="1.0.0"
)

# CORS middleware
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",") if os.getenv("ALLOWED_ORIGINS") else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir router de downloads
app.include_router(download.router)

@app.get("/")
async def read_root():
    """Health check"""
    return {"message": "Export Lambda", "status": "ok"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

