from abc import ABC, abstractmethod
from io import BytesIO
from fastapi import UploadFile
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from typing import Optional

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
            try:
                filename, content, content_type = attachment
                # Create an UploadFile object without setting content_type
                file = UploadFile(
                    filename=filename,
                    file=BytesIO(content)
                )

                # Set the attachment as a list of tuples
                message.attachments = [(file, {})]  # Empty dict for metadata
            except ValueError as e:
                print(f"Error unpacking attachment: {str(e)}")
        try:
            await self.fastmail.send_message(message)
        except Exception as e:
            raise  # Re-raise the exception after logging
