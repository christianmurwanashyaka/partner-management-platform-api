from abc import ABC, abstractmethod
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.models import Notification
from core.config import settings


class NotificationHandler(ABC):
    @abstractmethod
    async def send_notification(self, notification: Notification, attachment: Optional[tuple] = None):
        pass


class EmailNotificationHandler(NotificationHandler):
    def __init__(self):
        config = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            USE_CREDENTIALS=settings.USE_CREDENTIALS
        )
        self.fastmail = FastMail(config)

    async def send_notification(self, notification: Notification, attachment: Optional[tuple] = None):
        message = MessageSchema(
            subject=notification.subject,
            recipients=[notification.recipient.email],
            body=notification.message,
            subtype="html"
        )

        if attachment:
            filename, content, content_type = attachment
            message.attachments = [(filename, content, content_type)]

        await self.fastmail.send_message(message)