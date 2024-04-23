from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models.user import User
from helpers.db import get_first_item
from schemas.user import UserCreate, Token, LoginRequest, UserProfile
from utils.security import get_password_hash, verify_password, create_access_token

router = APIRouter()


@router.post("/signup", response_model=User)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await db.get(User, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        level=user.level,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
async def login_for_access_token(
        login_request: LoginRequest,
        db: AsyncSession = Depends(get_db)
):
    query = select(User).filter(User.email == login_request.email)
    user = await get_first_item(db, query)
    if not user or not verify_password(login_request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=UserProfile)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    return current_user
