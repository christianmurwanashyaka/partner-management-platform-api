import asyncio
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Optional

from fastapi import UploadFile
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

from core.config import settings
from db.models import Notification


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
            USE_CREDENTIALS=settings.USE_CREDENTIALS,
            VALIDATE_CERTS=False,
        )
        self.fastmail = FastMail(config)

    async def _send_email(self, message: MessageSchema, notification: Notification):
        try:
            await self.fastmail.send_message(message)
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            raise

    async def send_notification(self, notification: Notification, attachment: Optional[tuple] = None):
        message = MessageSchema(
            subject=notification.subject,
            recipients=[notification.recipient.email],
            body=notification.message,
            subtype="html",
        )

        if attachment:
            try:
                filename, content, content_type = attachment
                file = UploadFile(filename=filename, file=BytesIO(content))
                message.attachments = [(file, {})]  # Empty dict for metadata
            except ValueError as e:
                print(f"Error unpacking attachment: {str(e)}")

        try:
            asyncio.create_task(self._send_email(message, notification))
        except Exception as e:
            raise  # Re-raise the exception after logging


from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape


class TemplateHandler:
    def __init__(self):
        template_dir = Path(__file__).parent
        if not template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

    async def render_template(self, template_name: str, **kwargs) -> str:
        try:
            template = self.env.get_template(f"emails/{template_name}")
            kwargs['year'] = datetime.now().year
            return template.render(**kwargs, system_name=settings.SYSTEM_NAME)
        except Exception as e:
            raise Exception(f"Error rendering template: {str(e)}")
