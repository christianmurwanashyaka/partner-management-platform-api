import os
from datetime import datetime

from fastapi import UploadFile, HTTPException


async def handle_upload_file(file: UploadFile):
    upload_directory = 'uploads'
    os.makedirs(upload_directory, exist_ok=True)

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'{timestamp}_{file.filename}'
        file_path = os.path.join(upload_directory, filename)

        with open(file_path, 'wb+') as file_object:
            file_object.write(await file.read())

        return file_path, filename
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
