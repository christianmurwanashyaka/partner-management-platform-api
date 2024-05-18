from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models.organization import Organization
from db.models.user import User, UserRole, MOHStaffLevel
from helpers.db import get_first_item, check_if_exists, get_items_by_criteria
from schemas.user import UserCreate, Token, LoginRequest, UserProfile, SignupResponse, UserOrganization
from utils.security import get_password_hash, verify_password, create_access_token

router = APIRouter()


@router.post("/signup", response_model=SignupResponse)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    if await check_if_exists(User, db, email=user.email):
        raise HTTPException(status.HTTP_409_CONFLICT, detail='User with this email already exists')

    if user.role == UserRole.MOH_STAFF:
        if user.level is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Level is required for MOH Staff')
        if user.level not in MOHStaffLevel:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Invalid level for MOH Staff')

    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        level=user.level,
        created_by=user.email
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    token = create_access_token(data={"sub": user.email})
    return {"user": db_user, "token": {"access_token": token, "token_type": "bearer"}}


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
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "level": user.level
    }


@router.get("/users/me", response_model=UserProfile)
async def get_user_profile(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role == UserRole.PARTNER:
        query = select(Organization).where(Organization.created_by == current_user.email)
        organizations = await get_items_by_criteria(db, query)
        organization_summaries = [
            UserOrganization(
                uuid=org.uuid,
                name=org.name,
                email=org.email
            )
            for org in organizations
        ]
        return UserProfile(
            uuid=current_user.uuid,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            email=current_user.email,
            role=current_user.role,
            level=current_user.level,
            organizations=organization_summaries
        )
    else:
        return UserProfile(
            uuid=current_user.uuid,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            email=current_user.email,
            role=current_user.role,
            level=current_user.level
        )