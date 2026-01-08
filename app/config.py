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
    
    # Claude Configuration (AWS Bedrock)
    use_claude: bool = os.getenv("USE_CLAUDE", "false").lower() == "true"
    # AWS_REGION es automática en Lambda, usar boto3 para detectarla
    aws_region: str = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    claude_model: str = os.getenv("CLAUDE_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")
    claude_max_tokens: int = int(os.getenv("CLAUDE_MAX_TOKENS", "2000"))
    
    # Estrategia: qué documentos usar Claude
    claude_for_reports: bool = os.getenv("CLAUDE_FOR_REPORTS", "true").lower() == "true"
    claude_for_thesis: bool = os.getenv("CLAUDE_FOR_THESIS", "true").lower() == "true"
    claude_for_books: bool = os.getenv("CLAUDE_FOR_BOOKS", "true").lower() == "true"
    claude_as_validator: bool = os.getenv("CLAUDE_AS_VALIDATOR", "false").lower() == "true"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

