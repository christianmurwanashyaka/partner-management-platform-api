import logging
import mimetypes
import uuid
from typing import List, Optional
from fastapi import BackgroundTasks

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.config import settings
from db.models import (
    Notification,
    UserRole,
    User,
    MOHStaffLevel,
    MouApplication,
    Organization,
)
from templates.handlers import TemplateHandler
from .handlers import EmailNotificationHandler


async def create_and_send_notification(
    db: AsyncSession,
    email_handler: EmailNotificationHandler,
    recipient_id: uuid.UUID,
    subject: str,
    message: str,
    created_by: str,
    background_tasks: BackgroundTasks,
    attachment: Optional[tuple] = None,
):
    # Create the notification
    notification = Notification(
        recipient_id=recipient_id,
        subject=subject,
        from_email=settings.MAIL_FROM,
        message=message,
        is_read=False,
        created_by=created_by,
    )

    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    # Load the recipient
    recipient_query = select(User).where(User.uuid == notification.recipient_id)
    result = await db.execute(recipient_query)
    recipient = result.scalar_one_or_none()
    notification.recipient = recipient

    # Send the notification
    background_tasks.add_task(email_handler.send_notification, notification, attachment)


async def send_verification_email(
    db: AsyncSession,
    email_handler: EmailNotificationHandler,
    user: User,
    verification_token: str,
    background_tasks: BackgroundTasks,
):
    template_handler = TemplateHandler()
    verification_url = (
        f"{settings.FRONT_END_EMAIL_VERIFICATION_URL}?token={verification_token}"
    )
    html_content = await template_handler.render_template(
        "verification_email.html",
        user={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        },
        verification_url=verification_url,
    )

    await create_and_send_notification(
        db=db,
        email_handler=email_handler,
        recipient_id=user.uuid,
        subject="Verify Your Email Address",
        message=html_content,
        created_by=user.email,
        background_tasks=background_tasks,
    )


async def send_forgot_password_email(
    db: AsyncSession,
    email_handler: EmailNotificationHandler,
    user: User,
    reset_token: str,
    background_tasks: BackgroundTasks,
):
    template_handler = TemplateHandler()
    reset_url = f"{settings.FRONT_END_PASSWORD_RESET_URL}?reset_token={reset_token}"
    html_content = await template_handler.render_template(
        "forgot_password.html",
        user={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        },
        reset_url=reset_url,
    )

    await create_and_send_notification(
        db=db,
        email_handler=email_handler,
        recipient_id=user.uuid,
        subject="Forgot password",
        message=html_content,
        created_by=user.email,
        background_tasks=background_tasks,
    )


async def notify_partner_coordinators(
    db: AsyncSession,
    application_id: str,
    created_by: str,
    email_handler: EmailNotificationHandler,
    background_tasks: BackgroundTasks,
):
    # Query for all partner coordinators
    query = select(User).filter(
        User.role == UserRole.MOH_STAFF, User.level == MOHStaffLevel.PARTNER_COORDINATOR
    )
    result = await db.execute(query)
    partner_coordinators = result.scalars().all()

    for coordinator in partner_coordinators:
        await create_and_send_notification(
            db=db,
            email_handler=email_handler,
            recipient_id=coordinator.uuid,
            subject="New MOU Application Submitted",
            message=f"A new MOU application (ID: {application_id}) has been submitted and requires your review.",
            created_by=created_by,
            background_tasks=background_tasks,
        )


async def notify_moh_staff(
    db: AsyncSession,
    email_handler: EmailNotificationHandler,
    levels: List[MOHStaffLevel],
    created_by: str,
    subject: str,
    message: str,
    background_tasks: BackgroundTasks,
):
    # Query for all MOH staff with the specified levels
    query = select(User).filter(User.role == UserRole.MOH_STAFF, User.level.in_(levels))
    result = await db.execute(query)
    moh_staff = result.scalars().all()

    for staff in moh_staff:
        await create_and_send_notification(
            db=db,
            email_handler=email_handler,
            recipient_id=staff.uuid,
            subject=subject,
            message=message,
            created_by=created_by,
            background_tasks=background_tasks,
        )


async def notify_partner(
    db: AsyncSession,
    email_handler: EmailNotificationHandler,
    application_id: str,
    created_by: str,
    subject: str,
    message: str,
    background_tasks: BackgroundTasks,
    attachment_path: str = None,
    attachment_filename: str = None,
):
    # Get the partner's email associated with the application
    query = select(MouApplication.created_by).where(
        MouApplication.uuid == application_id
    )
    result = await db.execute(query)
    partner_email = result.scalar_one_or_none()

    if not partner_email:
        logging.error(f"Partner email not found for application ID: {application_id}")
        return

    # Get the partner's UUID
    partner_uuid_query = select(User.uuid).where(User.email == partner_email)
    partner_uuid_result = await db.execute(partner_uuid_query)
    partner_uuid = partner_uuid_result.scalar_one_or_none()

    if not partner_uuid:
        logging.error(f"Partner UUID not found for email: {partner_email}")
        return

    # Prepare attachment if provided
    attachment = None
    if attachment_path and attachment_filename:
        with open(attachment_path, "rb") as file:
            content = file.read()
        content_type = (
            mimetypes.guess_type(attachment_filename)[0] or "application/octet-stream"
        )
        attachment = (attachment_filename, content, content_type)

    # Send the email with or without attachment
    await create_and_send_notification(
        db=db,
        email_handler=email_handler,
        recipient_id=partner_uuid,
        subject=subject,
        message=message,
        created_by=created_by,
        attachment=attachment,
        background_tasks=background_tasks,
    )


async def notify_new_user(
    db: AsyncSession,
    email_handler: EmailNotificationHandler,
    user: User,
    organization: Organization,
    background_tasks: BackgroundTasks,
):
    template_handler = TemplateHandler()

    # Render the HTML template
    html_content = await template_handler.render_template(
        "welcome_email.html",
        user={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone_number": user.phone_number,
        },
        organization=organization
        and {
            "name": organization.name,
            "email": organization.email,
            "phone_number": organization.phone_number,
            "website": organization.website,
        },
    )

    # Create and send notification
    await create_and_send_notification(
        db=db,
        email_handler=email_handler,
        recipient_id=user.uuid,
        subject="Welcome to Our System",
        message=html_content,
        created_by=user.email,
        background_tasks=background_tasks,
    )


async def notify_new_organization(
    db: AsyncSession,
    email_handler: EmailNotificationHandler,
    user: User,
    organization: Organization,
    background_tasks: BackgroundTasks,
):
    subject = "Welcome to Our System - Your Organization Has Been Registered"
    message = f"""
    Dear {organization.name},

    Welcome to our system! Your organization has been successfully registered with the following details:

    Organization Information:
    - Name: {organization.name}
    - Email: {organization.email}
    - Phone: {organization.phone_number}
    - Website: {organization.website}
    - Rwanda Representative: {organization.rwanda_representative}

    We look forward to working with you. If you have any questions or need assistance, please don't hesitate to contact our support team.

    Best regards,
    The System Team
    """

    await create_and_send_notification(
        db=db,
        email_handler=email_handler,
        recipient_id=user.uuid,
        subject=subject,
        message=message,
        created_by=user.email,
        background_tasks=background_tasks,
    )
