from fastapi import Depends, HTTPException, status
from api.dependencies.auth import get_current_user
from db.models.user import User


async def admin_access(current_user: User = Depends(get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')
    return current_user


async def partner_access(current_user: User = Depends(get_current_user)):
    if current_user.role not in ['admin', 'partner']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')
    return current_user


async def swapteam_member_access(current_user: User = Depends(get_current_user)):
    if current_user.role not in ['admin', 'swapteam_member']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not authorized to perform this action')
    return current_user
