import os

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()


@router.get('/download', response_class=FileResponse)
async def download_document(file_path: str = Query(..., description="The path to the document to download")):
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, filename=os.path.basename(file_path))
