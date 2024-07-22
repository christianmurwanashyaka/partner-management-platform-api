from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.models import Notification, UserRole, User, MOHStaffLevel, MouApplication
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
    query = select(MouApplication.created_by).where(MouApplication.id == application_id)
    result = await db.execute(query)
    partner_email = result.scalar_one_or_none()

    if not partner_email:
        logging.error(f"Partner email not found for application ID: {application_id}")
        return

    notification = Notification(
        recipient_email=partner_email,
        subject=subject,
        from_email=settings.MAIL_FROM,
        message=message,
        is_read=False,
        created_by=created_by
    )

    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    # Send the email with attachment if provided
    if attachment_path and attachment_filename:
        await email_handler.send_notification_with_attachment(
            notification,
            attachment_path,
            attachment_filename
        )
    else:
        await email_handler.send_notification(notification)
