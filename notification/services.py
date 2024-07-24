import mimetypes
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.models import Notification, UserRole, User, MOHStaffLevel, MouApplication, Organization
import logging
from .handlers import EmailNotificationHandler
from core.config import settings


async def notify_partner_coordinators(db: AsyncSession, application_id: str, created_by: str, email_handler: EmailNotificationHandler):
    # Query for all partner coordinators
    query = select(User).filter(
        User.role == UserRole.MOH_STAFF,
        User.level == MOHStaffLevel.PARTNER_COORDINATOR
    )
    result = await db.execute(query)
    partner_coordinators = result.scalars().all()

    for coordinator in partner_coordinators:
        notification = Notification(
            recipient_id=coordinator.uuid,
            subject="New MOU Application Submitted",
            from_email=settings.MAIL_FROM,
            message=f"A new MOU application (ID: {application_id}) has been submitted and requires your review.",
            is_read=False,  # Set is_read here when creating the notification
            created_by=created_by
        )

        # Save the notification to the database
        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        # Send the email notification
        await email_handler.send_notification(notification)


async def notify_moh_staff(
        db: AsyncSession,
        email_handler: EmailNotificationHandler,
        levels: List[MOHStaffLevel],
        created_by: str,
        subject: str,
        message: str):
    # Query for all MOH staff with the specified levels
    query = select(User).filter(
        User.role == UserRole.MOH_STAFF,
        User.level.in_(levels)
    )
    result = await db.execute(query)
    moh_staff = result.scalars().all()

    for staff in moh_staff:
        notification = Notification(
            recipient_id=staff.uuid,
            subject=subject,
            from_email=settings.MAIL_FROM,
            message=message,
            is_read=False,
            created_by=created_by
        )

        # Save the notification to the database
        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        # Send the email notification
        await email_handler.send_notification(notification)


async def notify_partner(
    db: AsyncSession,
    email_handler: EmailNotificationHandler,
    application_id: str,
    created_by: str,
    subject: str,
    message: str,
    attachment_path: str = None,
    attachment_filename: str = None
):
    # Get the partner's email associated with the application
    query = select(MouApplication.created_by).where(MouApplication.uuid == application_id)
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

    notification = Notification(
        recipient_id=partner_uuid,
        from_email=settings.MAIL_FROM,
        subject=subject,
        message=message,
        is_read=False,
        created_by=created_by
    )

    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    # Prepare attachment if provided
    attachment = None
    if attachment_path and attachment_filename:
        with open(attachment_path, "rb") as file:
            content = file.read()
        content_type = mimetypes.guess_type(attachment_filename)[0] or "application/octet-stream"
        attachment = (attachment_filename, content, content_type)

    # Send the email with or without attachment
    await email_handler.send_notification(notification, attachment)


async def notify_new_user(db: AsyncSession, email_handler: EmailNotificationHandler, user: User, organization: Organization):
    subject = "Welcome to Our System - Your Account and Organization Details"
    message = f"""
    Dear {user.first_name} {user.last_name},

    Welcome to our system! Your account has been successfully created with the following details:

    User Profile:
    - Email: {user.email}
    - Phone: {user.phone_number}

    Organization Details:
    - Name: {organization.name}
    - Email: {organization.email}
    - Phone: {organization.phone_number}
    - Website: {organization.website}

    You can now log in to your account using your email and the password you provided during registration.

    If you have any questions or need assistance, please don't hesitate to contact our support team.

    Best regards,
    The System Team
    """

    notification = Notification(
        recipient_id=user.uuid,
        subject=subject,
        from_email=settings.MAIL_FROM,
        message=message,
        is_read=False,
        created_by=user.email
    )

    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    await email_handler.send_notification(notification)


async def notify_new_organization(db: AsyncSession, email_handler: EmailNotificationHandler, user: User, organization: Organization):
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

    notification = Notification(
        recipient_id=user.uuid,  # Using the existing user's UUID
        subject=subject,
        from_email=settings.MAIL_FROM,
        message=message,
        is_read=False,
        created_by=user.email
    )

    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    await email_handler.send_notification(notification)