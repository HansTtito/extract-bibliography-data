from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from io import BytesIO
from app.database import get_db
from app.services.export_service import ExportService

router = APIRouter(prefix="/api", tags=["Download"])


@router.get("/download/csv")
async def download_csv(db: Session = Depends(get_db)):
    """Descarga todos los documentos en formato CSV"""
    export_service = ExportService(db)
    csv_file = export_service.export_to_csv()
    
    return StreamingResponse(
        csv_file,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=documentos.csv"}
    )


@router.get("/download/excel")
async def download_excel(db: Session = Depends(get_db)):
    """Descarga todos los documentos en formato Excel"""
    try:
        export_service = ExportService(db)
        excel_file = export_service.export_to_excel()
        
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=documentos.xlsx"}
        )
    except Exception as e:
        import traceback
        error_detail = f"Error al generar archivo Excel: {str(e)}"
        print(f"{error_detail}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/download/json")
async def download_json(db: Session = Depends(get_db)):
    """Descarga todos los documentos en formato JSON"""
    export_service = ExportService(db)
    json_data = export_service.export_to_json()
    
    # Convertir string a BytesIO para StreamingResponse
    json_bytes = json_data.encode('utf-8')
    json_file = BytesIO(json_bytes)
    
    return StreamingResponse(
        json_file,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=documentos.json"}
    )

