from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import pdf_upload, reference_upload, documents, references_pdf_upload, s3_upload
import os

app = FastAPI(
    title="Plataforma de Extracción Bibliográfica",
    description="API para extraer información bibliográfica de PDFs y referencias",
    version="1.0.0"
)

# CORS middleware
# En producción, cambiar allow_origins a dominios específicos
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",") if os.getenv("ALLOWED_ORIGINS") else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers (download.router removido - va en Lambda separada)
app.include_router(pdf_upload.router)
app.include_router(reference_upload.router)
app.include_router(references_pdf_upload.router)
app.include_router(documents.router)
app.include_router(s3_upload.router)

# Servir archivos estáticos del frontend
if os.path.exists("frontend/static"):
    app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Servir index.html en la raíz
@app.get("/")
async def read_root():
    """Servir el frontend"""
    if os.path.exists("frontend/index.html"):
        return FileResponse("frontend/index.html")
    return {"message": "Plataforma de Extracción Bibliográfica API"}


@app.on_event("startup")
async def startup_event():
    """Inicializar base de datos al iniciar la aplicación"""
    try:
        init_db()
        print("✅ Base de datos inicializada correctamente")
    except Exception as e:
        print(f"⚠️ Error inicializando base de datos: {e}")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

