from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def handle_integrity_error(e: IntegrityError, db: AsyncSession):
    await db.rollback()
    error_message = str(e)

    if "duplicate key value violates unique constraint" in error_message:
        # Extract the duplicate key value from the error message
        try:
            duplicate_key = error_message.split("=")[1].split(")")[0]
        except IndexError:
            duplicate_key = "unknown field"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duplicate entry for {duplicate_key}"
        )
    else:
        # Handle other types of IntegrityError
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data provided"
        )
