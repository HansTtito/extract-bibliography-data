from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    database_url: str
    crossref_email: Optional[str] = None
    
    # GROBID Configuration
    use_grobid: bool = os.getenv("USE_GROBID", "false").lower() == "true"
    grobid_url: Optional[str] = os.getenv("GROBID_URL", None)
    grobid_timeout: int = int(os.getenv("GROBID_TIMEOUT", "30"))
    
    # Límites de tamaño
    max_pdf_size_mb: int = int(os.getenv("MAX_PDF_SIZE_MB", "10"))
    max_batch_count: int = int(os.getenv("MAX_BATCH_COUNT", "10"))
    max_batch_total_mb: int = int(os.getenv("MAX_BATCH_TOTAL_MB", "50"))
    
    # S3 bucket for PDF uploads
    s3_bucket: str = os.getenv("S3_BUCKET", "bibliografia-pdfs-sandbox-720081910880")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

