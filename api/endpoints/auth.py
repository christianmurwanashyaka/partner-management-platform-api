import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from api.dependencies.access_control import admin_access
from api.dependencies.auth import get_current_user
from api.dependencies.email_notification_handler import get_email_notification_handler
from db.database import get_db
from db.models.organization import Organization
from db.models.user import User, UserRole, MOHStaffLevel
from helpers.db import get_first_item, check_if_exists, get_items_by_criteria
from notification.handlers import EmailNotificationHandler
from notification.services import send_verification_email, send_forgot_password_email
from schemas.user import (
    UserCreate,
    Token,
    LoginRequest,
    UserProfile,
    SignupResponse,
    UserOrganization,
    ChangePasswordRequest,
    PasswordResetRequest,
)
from utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_verification_token,
    verify_token,
    create_reset_token,
    verify_reset_token,
)

router = APIRouter()


@router.post("/signup", response_model=SignupResponse)
async def create_user(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    email_handler: EmailNotificationHandler = Depends(get_email_notification_handler),
):
    if await check_if_exists(User, db, email=user.email):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="User with this email already exists"
        )

    if user.role == UserRole.MOH_STAFF:
        if user.level is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Level is required for MOH Staff"
            )
        if user.level not in MOHStaffLevel:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Invalid level for MOH Staff"
            )

    if user.role in [UserRole.DATA_MANAGER, UserRole.DATA_REPORTER]:
        if user.organization_uuid is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Organization UUID is required for Data Managers and Data Reporters",
            )

        # Check if the organization exists

        org_query = select(Organization).where(
            Organization.uuid == user.organization_uuid
        )
        result = await db.execute(org_query)
        organization = result.scalars().first()

        if not organization:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Organization not found"
            )

    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number,
        role=user.role,
        level=user.level,
        created_by=user.email,
        partner_organization_name=user.partner_organization_name,
        organization_uuid=(
            user.organization_uuid
            if user.role in [UserRole.DATA_MANAGER, UserRole.DATA_REPORTER]
            else None
        ),
        is_verified=False,
        has_set_password=False,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    verification_token = create_verification_token(user.email)
    await send_verification_email(
        db, email_handler, db_user, verification_token, background_tasks
    )

    return {"user": db_user}


@router.get("/verify/{token}")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    email = verify_token(token)

    query = select(User).where(User.email == email)
    result = await db.execute(query)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already verified"
        )

    user.is_verified = True
    await db.commit()

    return {"message": "Email verified successfully"}


@router.get("/resend-verification")
async def resend_verification_email(
    email: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    email_handler: EmailNotificationHandler = Depends(get_email_notification_handler),
):
    query = select(User).filter(User.email == email)
    user = await get_first_item(db, query)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already verified"
        )

    verification_token = create_verification_token(user.email)

    await send_verification_email(
        db, email_handler, user, verification_token, background_tasks
    )

    return {"message": "Verification email has been reset"}


@router.post("/login", response_model=Token)
async def login_for_access_token(
    login_request: LoginRequest, db: AsyncSession = Depends(get_db)
):
    query = select(User).filter(User.email == login_request.email)
    user = await get_first_item(db, query)

    if not user or not verify_password(login_request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before logging in. Check your email for the verification link.",
        )

    access_token = create_access_token(data={"sub": user.email})
    return {
        "uuid": user.uuid,
        "access_token": access_token,
        "token_type": "bearer",
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "level": user.level,
        "is_verified": user.is_verified,
        "has_set_password": user.has_set_password,
    }


@router.get("/users/me", response_model=UserProfile)
async def get_user_profile(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    query = select(Organization).where(
        (Organization.created_by == current_user.email)
        | (Organization.uuid == current_user.organization_uuid)
    )
    organizations = await get_items_by_criteria(db, query)
    organization_summaries = [
        UserOrganization(uuid=org.uuid, name=org.name, email=org.email)
        for org in organizations
    ]
    return UserProfile(
        uuid=current_user.uuid,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        email=current_user.email,
        role=current_user.role,
        level=current_user.level,
        organizations=organization_summaries if organization_summaries else None,
    )


@router.post(
    "/{uuid}/reset-password-to-default",
    response_model=UserProfile,
    dependencies=[Depends(admin_access)],
)
async def reset_password_to_default(
    uuid: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    try:
        query = select(User).where(User.uuid == uuid)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

        default_password = "1234"
        user.password = get_password_hash(default_password)
        await db.commit()
        await db.refresh(user)

        return user
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/change_password", response_model=UserProfile)
async def change_password(
    change_password_request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        if not verify_password(
            change_password_request.old_password, current_user.password
        ):
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, detail="Incorrect old password"
            )
        current_user.password = get_password_hash(change_password_request.new_password)

        await db.commit()
        await db.refresh(current_user)

        return current_user
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/forgot_password")
async def forgot_password(
    email: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    email_handler: EmailNotificationHandler = Depends(get_email_notification_handler),
):
    """
    Initiates the password reset process by sending a reset link to the user's email. The reset token is time-limited and single-use
    :param email:
    :param db:
    :param email_handler:
    :return:
    """
    try:
        query = select(User).filter(User.email == email)
        user = await get_first_item(db, query)

        if not user:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail=f"User with email {email} not found"
            )

        reset_token = create_reset_token(user.email)
        user.password_reset_token = get_password_hash(reset_token)
        user.password_reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        await db.commit()

        await send_forgot_password_email(
            db, email_handler, user, reset_token, background_tasks
        )

        return {"message": "Reset password email has been reset"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/reset_password/{token}")
async def reset_password(
    token: str, reset_request: PasswordResetRequest, db: AsyncSession = Depends(get_db)
):
    """
    Resets the user's password using a valid reset token.
    The token must not be expired and can only be used once.
    """

    try:
        email = verify_reset_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    query = select(User).filter(User.email == email)
    user = await get_first_item(db, query)

    if not user or not user.password_reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token"
        )

    if (
        user.password_reset_token_expires
        and user.password_reset_token_expires < datetime.utcnow()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token has expired"
        )

    if not verify_password(token, user.password_reset_token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token"
        )

    user.password = get_password_hash(reset_request.new_password)
    user.password_reset_token = None
    user.password_reset_token_expires = None

    await db.commit()

    return {"message": "Password has been reset successfully"}
