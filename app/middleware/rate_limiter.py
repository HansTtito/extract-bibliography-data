"""
Middleware para validar límites de tamaño de archivos
"""
import logging
from fastapi import HTTPException, UploadFile
from typing import List
from app.config import settings

logger = logging.getLogger(__name__)


def validate_pdf_size(file: UploadFile, max_size_mb: int = None) -> None:
    """
    Valida que el tamaño del PDF no exceda el límite
    
    Args:
        file: Archivo a validar
        max_size_mb: Tamaño máximo en MB (default: settings.max_pdf_size_mb)
        
    Raises:
        HTTPException: Si el archivo excede el límite
    """
    if max_size_mb is None:
        max_size_mb = settings.max_pdf_size_mb
    
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # Leer tamaño del archivo
    file.file.seek(0, 2)  # Ir al final
    file_size = file.file.tell()
    file.file.seek(0)  # Volver al inicio
    
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"El archivo excede el tamaño máximo de {max_size_mb}MB. Tamaño actual: {file_size / (1024 * 1024):.2f}MB"
        )
    
    logger.debug(f"Archivo validado: {file.filename}, tamaño: {file_size / (1024 * 1024):.2f}MB")


def validate_batch_size(files: List[UploadFile], max_count: int = None, max_total_mb: int = None) -> None:
    """
    Valida que el batch de archivos no exceda los límites
    
    Args:
        files: Lista de archivos a validar
        max_count: Número máximo de archivos (default: settings.max_batch_count)
        max_total_mb: Tamaño total máximo en MB (default: settings.max_batch_total_mb)
        
    Raises:
        HTTPException: Si el batch excede los límites
    """
    if max_count is None:
        max_count = settings.max_batch_count
    
    if max_total_mb is None:
        max_total_mb = settings.max_batch_total_mb
    
    max_total_bytes = max_total_mb * 1024 * 1024
    
    # Validar cantidad
    if len(files) > max_count:
        raise HTTPException(
            status_code=413,
            detail=f"El batch excede el número máximo de archivos ({max_count}). Archivos enviados: {len(files)}"
        )
    
    # Validar tamaño total
    total_size = 0
    for file in files:
        file.file.seek(0, 2)  # Ir al final
        file_size = file.file.tell()
        file.file.seek(0)  # Volver al inicio
        total_size += file_size
    
    if total_size > max_total_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"El tamaño total del batch excede el límite de {max_total_mb}MB. Tamaño total: {total_size / (1024 * 1024):.2f}MB"
        )
    
    logger.debug(f"Batch validado: {len(files)} archivos, tamaño total: {total_size / (1024 * 1024):.2f}MB")

